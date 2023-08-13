# -*- coding:utf-8 -*-
import argparse
from datetime import datetime
from pathlib import Path
import random
import time
from dataclasses import dataclass, field
import requests
from requests import Response
from markdownify import MarkdownConverter

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/61.0.3163.100 Safari/537.36",
    "Connection": "keep-alive",
    "Accept": "text/html,application/json,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.8"}


class ObsidianStyleConverter(MarkdownConverter):
    """
    Create a custom MarkdownConverter that adds two newlines after an image
    """
    attachments_save_dir: str

    @staticmethod
    def chomp(text):
        """
        If the text in an inline tag like b, a, or em contains a leading or trailing
        space, strip the string and return a space as suffix of prefix, if needed.
        This function is used to prevent conversions like
            <b> foo</b> => ** foo**
        """
        prefix = ' ' if text and text[0] == ' ' else ''
        suffix = ' ' if text and text[-1] == ' ' else ''
        text = text.strip()
        return prefix, suffix, text

    def convert_img(self, el, text, convert_as_inline):
        alt = el.attrs.get('alt', None) or ''
        src = el.attrs.get('src', None) or ''

        img_content_name = src.split('?')[0].split('/')[-1]
        img_path = Path(self.attachments_save_dir, img_content_name)
        if not img_path.is_file():
            Path(self.attachments_save_dir).mkdir(exist_ok=True)
            try:
                img_content = requests.get(url=src, headers=HEADERS).content
                with img_path.open('wb') as fp:
                    fp.write(img_content)
            except:
                img_content_name = src
                print(f"{src} download failed.")

        return f'![{alt}]({img_content_name})'

    def convert_a(self, el, text, convert_as_inline):
        prefix, suffix, text = self.chomp(text)
        if not text:
            return ''
        href = el.get('href')
        # title = el.get('title')

        if el.get('aria-labelledby') and el.get('aria-labelledby').find('ref') > -1:
            text = text.replace('[', '[^')
            return '%s' % text

        if (el.attrs and 'data-reference-link' in el.attrs) or (
                'class' in el.attrs and el.attrs['class'] and ('ReferenceList-backLink' in el.attrs['class'])):
            text = '[^{}]: '.format(href[5])
            return '%s' % text

        return super().convert_a(el, text, convert_as_inline)

    def convert_li(self, el, text, convert_as_inline):
        if el and el.find('a', {'aria-label': 'back'}) is not None:
            return '%s\n' % ((text or '').strip())

        return super().convert_li(el, text, convert_as_inline)


@dataclass
class Item:
    id: str = ""
    url: str = ""
    type: str = ""
    title: str = ""
    # question_id = ""
    # question_desc = ""
    author_name: str = ""
    author_url: str = ""
    column_title: str = ""
    column_url: str = ""
    created_time: int = 0
    updated_time: int = 0
    content: str = ""


@dataclass
class Collection:
    id: str = ""
    url: str = ""
    title: str = ""
    items: list[Item] = field(default_factory=list)


# 解析出每个回答的具体链接
def get_collection(collection_id: str) -> Collection:
    collection = Collection()
    collection.id = collection_id

    try:
        url = f"https://www.zhihu.com/api/v4/collections/{collection_id}"
        html = requests.get(url, headers=HEADERS)
        html.raise_for_status()
        data = html.json()

        collection.item_count = data['collection']['item_count']
        collection.title = data['collection']['title']

    except:
        return None

    items = []
    collection.items = items
    offset = 0
    limit = 20
    i = 0
    page_num = 1
    while offset < collection.item_count:
        url = f"https://www.zhihu.com/api/v4/collections/{collection_id}/items?offset={offset}&limit={limit}"
        try:
            html: Response = requests.get(url, headers=HEADERS)
            content = html.json()
        except:
            return None

        print("page_num = ", page_num)
        print("offset = ", offset)
        print("list_size = ", len(content['data']))
        for el in content['data']:
            item = Item()
            items.append(item)
            item.id = el['content']['id']
            item.url = el['content']['url']
            item.type = el['content']['type']
            if item.type == 'answer':
                item.title = el['content']['question']['title']
                item.content = el['content']['content']
                # item.question_id = el['content']['question']['id']
            elif item.type == 'pin':
                # item.title = el['content']['excerpt_title']
                item.content = el['content']['content'][0]['content']
            elif item.type == 'article':
                item.title = el['content']['title']
                item.content = el['content']['content']
                if 'column' in el['content']:
                    item.column_title = el['content']['column']['title']
                    item.column_url = el['content']['column']['url']
            elif item.type == 'zvideo':
                pass
            else:
                item.content = el['content']['content']

            item.author_name = el['content']['author']['name']
            item.author_url = el['content']['author']['url']

            key_names = [('created', 'updated'),
                         ('created_time', 'updated_time'),
                         ('created_at', 'updated_at')]

            for pair in key_names:
                if pair[0] in el['content']:
                    item.created_time = el['content'][pair[0]]
                    item.updated_time = el['content'][pair[1]]
                    break

            i += 1
            print(f"{i}/{collection.item_count} - {item.id}")
        page_num += 1
        print("---")

        offset += limit
        time.sleep(random.uniform(0.5, 3.0))

    return collection


def save_collection(collection: Collection, download_dir: str, date_suffix: bool, overwrite_existed: bool = False):
    collection_title = "".join(x for x in collection.title if (x.isalnum() or x in "._- "))
    if date_suffix:
        collection_title += "_" + time.strftime("%Y%m%d")

    Path(download_dir, collection_title).mkdir(parents=True, exist_ok=True)

    i = 0
    for item in collection.items:
        print(f"{i + 1}/{len(collection.items)}\t{collection_title}/{item.id}.md")
        if item.content:
            convertor = ObsidianStyleConverter(heading_style="ATX")
            convertor.attachments_save_dir = f"{download_dir}/{collection_title}/attachments"
            md = convertor.convert(item.content)
        elif item.type == "zvideo":
            md = f"[{item.url}]({item.url})"

        created_time = datetime.utcfromtimestamp(item.created_time).strftime('%Y-%m-%d %H:%M:%S')
        updated_time = datetime.utcfromtimestamp(item.updated_time).strftime('%Y-%m-%d %H:%M:%S')
        metadata = ""
        metadata += f"---\n"
        metadata += f'id: "{item.id}"\n'
        metadata += f'url: "{item.url}"\n'
        metadata += f'type: "{item.type}"\n'
        if item.title:
            title = item.title\
                .replace('"', '\\"')\
                .replace('\\', '\\\\')
            metadata += f'title: "{title}"\n'
        if item.column_url:
            metadata += f'column: "[{item.column_title}]({item.column_url})"\n'
        metadata += f'published: "{created_time}"\n'
        metadata += f'updated: "{updated_time}"\n'
        metadata += "---\n\n"
        if item.title:
            metadata += f"# {item.title}\n\n"
        md = metadata + md

        path = Path(download_dir, collection_title, f"{item.id}.md")
        if (not overwrite_existed) and path.is_file():
            pass
        else:
            with path.open("w", encoding='utf-8') as md_file:
                md_file.write(md)

        i += 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='下载知乎收藏夹')
    parser.add_argument('collection_id', type=str, help="收藏夹链接末尾的数字ID")
    parser.add_argument('download_dir', type=str, nargs="?", help="下载路径，默认为~/zhihu_collections", default=str(Path.home()/"zhihu_collections"))
    parser.add_argument('-S', '--date_suffix', action="store_true", help='收藏夹文件名是否用日期作为后缀')
    parser.add_argument('-f', '--overwrite_existed', action="store_true", help='是否覆盖已存在的md文件')
    args = parser.parse_args()
    collection_inst = get_collection(args.collection_id)
    save_collection(collection_inst, args.download_dir, args.date_suffix, args.overwrite_existed)

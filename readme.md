将知乎公开收藏夹的内容分别保存为 Obsidian 适用的 Markdown 文件。

文件夹以收藏夹名字命名；视频只会保存为链接。

代码 Forked 自 https://github.com/Geralt-TYH/obsidian-zhihu-crawler ，仅为自用略作调整。

## 说明

```bash
pip install -r requirements.txt
```
### 用法
```
python main.py collection_id [download_dir] [-S|--date_suffix] [-f|--overwrite_existed]
```

`collection_id` - 收藏夹链接末尾的数字ID。

`download_dir` - 下载目录路径，不输入则默认为当前用户目录下的`zhihu_collections`文件夹。

`-S`或`--date_suffix` - 输入则将收藏夹ID加到文件名后作为日期后缀。

`-f`或`--overwrite_existed` - 输入则覆盖已经存在的同名 .md 文件。

### 示例

下载 ID 为 12345 的收藏夹到 Documents 文件夹，并覆盖已下载的文件:

```
python main.py 12345 "~/Documents/" -f
```


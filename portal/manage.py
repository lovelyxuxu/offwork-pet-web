"""Publish from a trusted local machine: python -m portal.manage --help."""
import argparse
import json
import os
from pathlib import Path

from .catalog import Catalog


def main():
    parser = argparse.ArgumentParser(description='下班搭子资源库发布工具')
    parser.add_argument('--data-dir', default=os.environ.get('OFFWORK_WEB_DATA', 'var'))
    sub = parser.add_subparsers(dest='command', required=True)
    add = sub.add_parser('import-pack', help='导入包，生成预览并登记版本')
    add.add_argument('paths', nargs='+', type=Path)
    release = sub.add_parser('import-release', help='导入发布者的版本清单，仅用于网站展示')
    release.add_argument('manifest', type=Path)
    for command in ['hide', 'show']:
        toggle = sub.add_parser(command)
        toggle.add_argument('identifier')
    sub.add_parser('list')
    args = parser.parse_args()
    catalog = Catalog(args.data_dir)
    if args.command == 'import-pack':
        for path in args.paths:
            files = sorted(path.glob('*.petpack')) if path.is_dir() else [path]
            if not files:
                raise ValueError('目录中没有角色包')
            for pack in files:
                item = catalog.import_pack(pack)
                print(f"已导入 {item['name']} {item['version']}")
    elif args.command == 'import-release':
        print('已登记软件版本 ' + catalog.import_release(args.manifest)['version'])
    elif args.command in ('hide', 'show'):
        catalog.set_visible(args.identifier, args.command == 'show')
        print('已更新上下架状态')
    else:
        print(json.dumps(catalog.characters(), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

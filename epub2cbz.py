# =====================================================================
# ファイル名: epub2cbz.py
# バージョン: 2.3.0
# タイムスタンプ: 2026-09-30
# 作者: emmmanime
# 処理概要: 
#   - EPUBを解析し、正しい読書順（spineまたはファイル名）で画像を抽出。
#   - spineにXHTMLが含まれる場合、中身を解析して<img>タグから画像パスを抽出。
#   - 「cover」関連の画像を自動検出し、先頭（0000番）に固定配置。
#   - 再帰的なフォルダ探索、位置引数による入力指定、出力先指定、
#     一括上書き（u）対応の上書き確認、ffmpeg風の独自ヘルプ表示に対応。
#   - i18n対応
# =====================================================================

import os
import sys
import zipfile
import argparse
import re
import json
import xml.etree.ElementTree as ET
from pathlib import Path

AUTHOR = "emmmanime"
VERSION = "2.3.0"

def load_i18n():
    i18n_path = Path(sys.argv[0]).resolve().parent / "epub2cbz.i18n"
    i18n_data = {}
    if i18n_path.exists():
        try:
            with open(i18n_path, 'r', encoding='utf-8') as f:
                i18n_data = json.load(f)
        except Exception as e:
            print(f"[Warning] Failed to load i18n file: {e}")
    return i18n_data

def get_language(i18n_data):
    script_name = Path(sys.argv[0]).stem
    match = re.search(r'_([a-z]{2})$', script_name)
    if match:
        return match.group(1)
    return i18n_data.get('init', {}).get('default_language', 'en')

I18N_DATA = load_i18n()
CURRENT_LANG = get_language(I18N_DATA)

def _t(key, **kwargs):
    lang_dict = I18N_DATA.get('languages', {}).get(CURRENT_LANG, {})
    text = lang_dict.get(key)
    if not text:
        en_dict = I18N_DATA.get('languages', {}).get('en', {})
        text = en_dict.get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
    return text

def print_version_banner():
    print(_t("version_banner", version=VERSION, author=AUTHOR))
    print(_t("version_desc1"))
    print(_t("version_desc2"))

def print_custom_help():
    print_version_banner()
    print(_t("app_desc"))
    print(_t("usage"))
    print()
    print(_t("getting_help"))
    print(_t("help_basic"))
    print(_t("help_detailed"))
    print()
    print(_t("global_options"))
    print(_t("help_path"))
    print(_t("help_output"))
    print(_t("help_force"))
    print(_t("help_verbose"))
    print(_t("help_license"))
    print(_t("help_version"))

def is_valid_cover(filename):
    stem = Path(filename).stem.lower()
    allowed_affixes = {'front', 'art', 'title', 'page', 'hyoushi', 'hyoshi'}
    
    words = re.split(r'[^a-z0-9]+', stem)
    
    if 'cover' in words:
        extra_words = [w for w in words if w != 'cover']
        if all(w in allowed_affixes or w.isdigit() for w in extra_words):
            return True, len(extra_words)
            
    if stem == 'coverart':
        return True, 1
        
    for affix in allowed_affixes:
        if stem == f"{affix}cover" or stem == f"cover{affix}":
            return True, 1
            
    return False, 999

def convert_epub_to_cbz(epub_path, output_cbz_path, force=False, verbose=False, overwrite_all_state=None):
    if output_cbz_path.exists() and not force:
        if overwrite_all_state and overwrite_all_state[0]:
            pass  
        else:
            print(_t("file_exists", filename=output_cbz_path.name))
            while True:
                response = input(_t("overwrite_prompt")).strip().lower()
                if response in ('y', 'yes'):
                    break
                elif response in ('n', 'no'):
                    print(_t("skip_msg"))
                    return
                elif response in ('u', 'all'):
                    if overwrite_all_state is not None:
                        overwrite_all_state[0] = True
                    break
                else:
                    print(_t("invalid_input"))

    if verbose:
        print(_t("process_start", filename=epub_path.name))
    else:
        print(_t("process_start_short", filename=epub_path.name), end="", flush=True)
    
    try:
        with zipfile.ZipFile(epub_path, 'r') as epub:
            namelist = epub.namelist()
            
            if verbose:
                print(_t("total_files_zip", count=len(namelist)))
            
            opf_path = None
            for name in namelist:
                if name.endswith('.opf'):
                    opf_path = name
                    break
            
            image_files = []
            
            if opf_path:
                if verbose:
                    print(_t("found_opf", opf_path=opf_path))
                try:
                    opf_content = epub.read(opf_path)
                    root = ET.fromstring(opf_content)
                    ns = {'opf': 'http://www.idpf.org/2007/opf', 'dc': 'http://purl.org/dc/elements/1.1/'}
                    
                    manifest = {}
                    for item in root.findall('.//opf:item', ns):
                        item_id = item.get('id')
                        href = item.get('href')
                        media_type = item.get('media-type', '')
                        
                        base_dir = Path(opf_path).parent
                        full_path = str(base_dir / href).replace('\\', '/')
                        manifest[item_id] = {
                            'path': os.path.normpath(full_path).replace('\\', '/'),
                            'media_type': media_type
                        }

                    spine_items = []
                    for itemref in root.findall('.//opf:itemref', ns):
                        idref = itemref.get('idref')
                        if idref in manifest:
                            item_info = manifest[idref]
                            item_path = item_info['path']
                            item_media = item_info['media_type']
                            
                            if item_media.startswith('image/'):
                                spine_items.append(item_path)
                            elif item_media in ('application/xhtml+xml', 'text/html'):
                                try:
                                    html_content = epub.read(item_path).decode('utf-8', errors='ignore')
                                    img_matches = re.findall(r'(?i)<(?:img|image)[^>]+(?:src|href)\s*=\s*["\']([^"\']+)["\']', html_content)
                                    
                                    for img_src in img_matches:
                                        img_src = img_src.split('#')[0].split('?')[0]
                                        img_full_path = str(Path(item_path).parent / img_src).replace('\\', '/')
                                        img_full_path = os.path.normpath(img_full_path).replace('\\', '/')
                                        spine_items.append(img_full_path)
                                except Exception as ex:
                                    if verbose:
                                        print(_t("html_parse_err", item_path=item_path, ex=ex))
                    
                    if spine_items:
                        image_files = spine_items
                        if verbose:
                            print(_t("image_order_count", count=len(image_files)))
                except Exception as e:
                    if verbose:
                        print(_t("opf_parse_err", ex=e))
            
            if not image_files:
                all_images = [n for n in namelist if n.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
                all_images.sort()
                image_files = all_images
                if verbose:
                    print(_t("fallback_count", count=len(image_files)))

            cover_candidates = []
            other_images = []
            
            for img in image_files:
                img_stem = Path(img).stem
                is_cover, score = is_valid_cover(img_stem)
                if is_cover:
                    cover_candidates.append((score, img))
                else:
                    other_images.append(img)
            
            cover_candidates.sort(key=lambda x: x[0])
            
            final_image_list = []
            selected_cover = None
            if cover_candidates:
                selected_cover = cover_candidates[0][1]
                final_image_list.append(selected_cover)
                if verbose:
                    print(_t("cover_detected", filename=selected_cover))
                for _, img in cover_candidates[1:]:
                    other_images.append(img)
            
            final_image_list.extend(other_images)

            if verbose:
                print(_t("final_page_list", count=len(final_image_list)))
                for idx, img_path in enumerate(final_image_list):
                    prefix = _t("page_prefix") if idx == 0 and selected_cover else ""
                    print(f"     Page {idx:04d}: {img_path}{prefix}")

            output_cbz_path.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(output_cbz_path, 'w', zipfile.ZIP_STORED) as cbz:
                for index, img_name in enumerate(final_image_list):
                    try:
                        img_data = epub.read(img_name)
                        ext = Path(img_name).suffix
                        
                        if index == 0 and selected_cover:
                            new_filename = f"0000{ext}"
                        else:
                            page_num = index if selected_cover else index + 1
                            new_filename = f"{page_num:04d}{ext}"
                            
                        cbz.writestr(new_filename, img_data)
                        if verbose:
                            print(_t("write_success", img_name=img_name, new_filename=new_filename))
                    except KeyError:
                        if verbose:
                            print(_t("file_not_found", img_name=img_name))
                    
        if not verbose:
            print(_t("done_short", count=len(final_image_list)))
        else:
            print(_t("done_verbose", output_path=output_cbz_path))

    except Exception as e:
        if not verbose:
            print(_t("fail_short"))
        print(_t("fail_msg", filename=epub_path.name, ex=e))

def main():
    if len(sys.argv) == 1:
        print_custom_help()
        sys.exit(0)

    for arg in sys.argv[1:]:
        if arg in ('-v', '--version'):
            print_version_banner()
            sys.exit(0)
        if arg in ('-L', '--license'):
            print(f"epub2cbz version {VERSION}")
            print(_t("license_msg1"))
            print(_t("license_msg2"))
            sys.exit(0)
        if arg in ('-h', '--help'):
            print_version_banner()
            print(_t("app_desc"))
            print(_t("usage"))
            print()
            print(_t("getting_help"))
            print(_t("help_basic"))
            print(_t("help_detailed"))
            print()
            print(_t("print_help_info"))
            print(_t("help_license"))
            print(_t("help_version"))
            print()
            print(_t("global_options"))
            print(_t("help_path"))
            print(_t("help_output"))
            print(_t("help_force"))
            print(_t("help_verbose"))
            print()
            sys.exit(0)

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("path", nargs="?", default=".")
    parser.add_argument("-o", "--output", default=None)
    parser.add_argument("-f", "--force", action="store_true")
    parser.add_argument("-V", "--verbose", action="store_true")
    parser.add_argument("-L", "--license", action="store_true")
    parser.add_argument("-v", "--version", action="store_true")
    parser.add_argument("-h", "--help", action="store_true")

    try:
        args, unknown = parser.parse_known_args()
    except Exception:
        print_custom_help()
        sys.exit(1)

    target_path = Path(args.path)
    output_dir = Path(args.output) if args.output else None

    if not target_path.exists():
        print(_t("err_path_not_exist", target_path=target_path))
        sys.exit(1)

    epub_files = []
    if target_path.is_file():
        if target_path.suffix.lower() == '.epub':
            epub_files.append(target_path)
        else:
            print(_t("err_not_epub", target_path=target_path))
            sys.exit(1)
    elif target_path.is_dir():
        epub_files = list(target_path.glob('**/*.epub'))

    if not epub_files:
        print(_t("no_epub_found"))
        sys.exit(0)

    print(_t("total_found", count=len(epub_files)) + "\n")

    overwrite_all_state = [False]

    for epub_file in epub_files:
        if output_dir:
            relative_path = epub_file.relative_to(target_path if target_path.is_dir() else target_path.parent)
            cbz_file = output_dir / relative_path.with_suffix('.cbz')
        else:
            cbz_file = epub_file.with_suffix('.cbz')

        convert_epub_to_cbz(
            epub_file, 
            cbz_file, 
            force=args.force, 
            verbose=args.verbose, 
            overwrite_all_state=overwrite_all_state
        )

    print(_t("all_done"))

if __name__ == "__main__":
    main()

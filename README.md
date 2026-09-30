# epub2cbz

A hyper-fast, cross-platform CLI tool to convert EPUB files to CBZ format with perfectly sorted reading order. It ensures that your pages are in the exact order intended by the publisher by intelligently parsing the EPUB `spine` and XHTML files, breaking free from the limitations of simple ZIP conversions.

## Key Features

- **Perfect Reading Order**: Accurately parses EPUB `opf` spine and embedded XHTML `<img>` tags to extract the true page sequence. Say goodbye to mangled page orders!
- **Cover Page Detection**: Automatically identifies cover pages and fixes them to `0000.ext`, with remaining pages starting at `0001.ext`. Optimized for comic readers.
- **Batch Processing**: Recursively scans folders (`**/*.epub`) and processes multiple files in one go.
- **i18n Support**: Native multi-language support (English/Japanese) without external dependencies. Just append the language code to the executable (e.g., `epub2cbz_ja.exe`) to switch languages.
- **No External Dependencies**: Built entirely with Python standard libraries for ultimate portability.

## Usage

```bash
epub2cbz [options] [path_to_epub_or_folder]
```

### Options

- `-o, --output <dir>`: Specify output directory.
- `-f, --force`: Force overwrite existing files without confirmation.
- `-V, --verbose`: Show detailed parsing and extraction logs.
- `-h, --help`: Show help message.
- `-v, --version`: Show version info.
- `-L, --license`: Show license (GPL-3.0).

## i18n Configuration

The tool uses `epub2cbz.i18n` (a JSON file) for localization.
If you build the script with PyInstaller, name the executable `epub2cbz_ja.exe` to enforce Japanese, or `epub2cbz.exe` to default to English.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

#!/bin/bash
# レポートPDFを作成（docs/report/report.html → PDF）
cd "$(dirname "$0")/.."
OUT=${1:-docs/report/説明資料_PAI最終課題_minotaro.pdf}
google-chrome --headless --no-pdf-header-footer --print-to-pdf="$OUT" "file://$PWD/docs/report/report.html"

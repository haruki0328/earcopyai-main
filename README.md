# AI Guitar Tab Creator

MP3/WAV音源をアップロードするだけで、AIがギターパートを抽出し、自動でTAB譜（タブ譜）を生成するWebアプリです。

## システムの目的

「この曲を弾きたいけどTAB譜がない」「耳コピをする時間やスキルがない」というギタリストの悩みを解決するために作りました。既存の自動採譜ソフトの多くはピアノ（MIDI）向けの出力が中心で、ギタリストが必要とする6本弦のTAB譜形式には対応していないものが多いです。本アプリは、手持ちの音源から誰でも瞬時に視認性の高いギターTAB譜を得られることを目指しています。

## 技術構成

- フロントエンド・UI: Streamlit
- バックエンド: Python 3.8
- 音源分離AI: Demucs（楽曲からギターの音のみを抽出）
- 自動採譜AI: Omnizart（分離したギター音源を音符データに変換）
- 主要ライブラリ: PrettyMIDI, NumPy, Pandas

## 特徴

- **複合AIによる音源抽出**: Demucsで楽曲からギターパートのみを分離し、ドラムやボーカルに影響されずに解析できます。
- **ギタリスト視点のTAB変換**: AIが出力した音程データを、低音弦を優先的に使うロジックでポジションに配置し、演奏しやすいTAB譜にしています。
- **カポタスト・移調対応**: カポ位置（0〜7フレット）や移調（±12半音）を指定すると、フレット表示を自動補正します。
- **インタラクティブなUI**: 解析結果を見ながら、TAB譜の上下反転や表示の折り返しをリアルタイムで調整できます。

## セットアップ

事前にFFmpegのインストールが必要です。

```bash
git clone https://github.com/haruki0328/earcopyai-main.git
cd earcopyai-main

conda env create -f environment.yml --prefix ./venv
conda activate ./venv

omnizart download-checkpoints
```

## 使い方

```bash
streamlit run main.py
```

1. 画面中央からMP3/WAVファイルをアップロード
2. サイドバーでカポ位置・使用モデル・移調を設定
3. 「解析スタート」を押すと、Demucsによるギター音源分離 → Omnizartによる採譜 → TAB譜生成の順に処理が進みます
4. 生成されたTAB譜とMIDIファイルはダウンロードして練習に使えます

## ファイル構成

| ファイル | 役割 |
|---|---|
| `main.py` | Streamlitによる画面・UI制御 |
| `logic.py` | Demucs/Omnizartの呼び出し、TAB譜への変換ロジック |
| `run_omnizart.py` | Omnizart単体での実行用スクリプト |
| `environment.yml` | conda環境定義 |
| `guitar.mid` | 動作確認用のサンプルMIDI |

## 注意点

- 音源分離・解析にはGPU環境を含むローカルセットアップが必要で、PCのスペックによっては数分かかります。
- 解析対象の音源ファイルおよび生成物は著作権保護の観点からリポジトリに含めていません。

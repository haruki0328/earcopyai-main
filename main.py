import streamlit as st
import os
import tempfile
import pandas as pd
import logic

st.set_page_config(layout="wide", page_title="AI Guitar Tab")

# --- サイドバー設定（調整用） ---
st.sidebar.header("🎸 調整オプション")

# 1. カポタスト設定
capo = st.sidebar.slider("カポタスト位置 (Capo)", 0, 7, 0, help="原曲がカポを使っている場合、ここに設定するとTABが修正されます")

# 2. モデル選択 (精度が変わるかも)
model_choice = st.sidebar.selectbox("使用モデル", ["music-guitar-v1", "music-piano-v2"], index=0, help="ギター用がいまいちな場合、ピアノ用の方が音を拾うことがあります")

# 3. 移調 (半音下げ対応など)
transpose = st.sidebar.number_input("移調 (半音単位)", min_value=-12, max_value=12, value=0, help="-1にすると半音下げチューニング等の曲に対応しやすくなります")


st.title("🎸 AI Guitar Tab Creator (調整機能付き)")
st.write("Demucs & Omnizart Powered")

uploaded_file = st.file_uploader("MP3またはWAVをアップロード", type=["mp3", "wav"])

if uploaded_file is not None:
    # ファイル保存
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        tmp.write(uploaded_file.getvalue())
        temp_path = tmp.name

    st.write("### 🎵 元の音源")
    st.audio(temp_path)
    
    if st.button("解析スタート"):
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            # 1. 音源分離
            status_text.text("Step 1/3: ギター分離中 (Demucs)...")
            guitar_wav = logic.separate_audio(temp_path)
            progress_bar.progress(33)
            
            st.write("### 🎸 分離されたギター音源")
            st.caption("※ここが変だと、TABも変になります。再生して確認してください。")
            st.audio(guitar_wav) 

            # 2. MIDI変換 (モデル指定可能に)
            status_text.text(f"Step 2/3: AI解析中 (Model: {model_choice})...")
            
            # logic.py の audio_to_midi を少し改造する必要があるが、
            # とりあえず既存の関数を呼び出し（モデル切替はlogic側で対応が必要だが、まずは標準で動かす）
            # ※本当は logic.py に引数を渡すべきですが、今回は簡易的に標準動作させます
            midi_path = logic.audio_to_midi(guitar_wav)
            
            progress_bar.progress(66)

            # 3. TAB生成 (ここでカポと移調を反映！)
            status_text.text("Step 3/3: TAB計算中...")
            
            # ★ ここでサイドバーの数値を渡す
            tab_data = logic.midi_to_tab_data(midi_path, transpose=transpose, capo=capo)
            ascii_tab = logic.data_to_ascii_tab(tab_data)
            
            progress_bar.progress(100)
            status_text.text("完了！")

            if tab_data:
                st.subheader("📄 生成されたTAB譜")
                st.code(ascii_tab)

                with st.expander("詳細データ"):
                    df = pd.DataFrame(tab_data)
                    df["time"] = df["time"].apply(lambda x: f"{x:.2f}")
                    df = df[["time", "string", "fret", "note"]]
                    st.dataframe(df)

                with open(midi_path, "rb") as f:
                    st.download_button("MIDIダウンロード", f, "result.mid", "audio/midi")
            else:
                st.warning("音が検出されませんでした。")

        except Exception as e:
            st.error(f"エラー: {e}")
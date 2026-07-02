import streamlit as st
import os
import tempfile
import pandas as pd
import logic

st.set_page_config(layout="wide", page_title="AI Guitar Tab")

st.sidebar.header(" 調整オプション")

capo = st.sidebar.slider("カポタスト位置 (Capo)", 0, 7, 0, help="原曲がカポを使っている場合、ここに設定するとTABが修正されます")
model_choice = st.sidebar.selectbox("使用モデル", ["music-guitar-v1", "music-piano-v2"], index=0, help="ギター用がいまいちな場合、ピアノ用の方が音を拾うことがあります")
transpose = st.sidebar.number_input("移調 (半音単位)", min_value=-12, max_value=12, value=0, help="-1にすると半音下げチューニング等の曲に対応しやすくなります")

st.title(" AI Guitar Tab Creator (調整機能付き)")
st.write("Demucs & Omnizart Powered")

uploaded_file = st.file_uploader("MP3またはWAVをアップロード", type=["mp3", "wav"])

if uploaded_file is not None:
    tmp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        st.write("###  元の音源")
        st.audio(tmp_path)

        if st.button("解析スタート"):
            progress_bar = st.progress(0)
            status_text = st.empty()

            status_text.text("Step 1/3: ギター分離中 (Demucs)...")
            guitar_wav = logic.separate_audio(tmp_path)
            progress_bar.progress(33)

            st.write("###  分離されたギター音源")
            st.caption("※ここが変だと、TABも変になります。再生して確認してください。")
            st.audio(guitar_wav)

            status_text.text(f"Step 2/3: AI解析中 (Model: {model_choice})...")
            midi_path = logic.audio_to_midi(guitar_wav, model_name=model_choice)
            progress_bar.progress(66)

            status_text.text("Step 3/3: TAB計算中...")
            tab_data = logic.midi_to_tab_data(midi_path, transpose=transpose, capo=capo)
            ascii_tab = logic.data_to_ascii_tab(tab_data)

            progress_bar.progress(100)
            status_text.text("完了！")

            if tab_data:
                st.subheader(" 生成されたTAB譜")
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
        st.error(f"解析中にエラーが発生しました: {e}")

    finally:
        # 一時ファイルは処理の成否に関わらず削除する
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

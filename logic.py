import os
import subprocess
import glob
import sys
import pretty_midi
from omnizart.music import app as mapp

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 開放弦のMIDIノート番号（1弦=64 〜 6弦=40、レギュラーチューニング）
GUITAR_STRINGS = [40, 45, 50, 55, 59, 64]


def separate_audio(input_path):
    print("--- Demucsで分離中 ---")
    command = [sys.executable, "-m", "demucs", "-n", "htdemucs_6s", "--two-stems", "guitar", "-o", OUTPUT_DIR, input_path]
    subprocess.run(command, check=True)

    filename = os.path.splitext(os.path.basename(input_path))[0]
    search_path = os.path.join(OUTPUT_DIR, "htdemucs_6s", filename, "guitar.wav")
    if os.path.exists(search_path):
        return search_path

    # demucsのバージョンによって出力パスが変わることがあるので保険で全探索
    found_all = glob.glob(os.path.join(OUTPUT_DIR, "**", "guitar.wav"), recursive=True)
    if found_all:
        return found_all[-1]
    raise FileNotFoundError("ギター音源が見つかりませんでした")

def audio_to_midi(audio_path, model_name="music-guitar-v1"):
    print(f"--- Omnizartで解析中 (Model: {model_name}) ---")
    output_midi_dir = os.path.join(OUTPUT_DIR, "midi")
    os.makedirs(output_midi_dir, exist_ok=True)

    filename = os.path.splitext(os.path.basename(audio_path))[0]
    midi_path = os.path.join(output_midi_dir, f"{filename}_omnizart.mid")

    try:
        midi = mapp.transcribe(audio_path, model_path=model_name)
    except Exception as e:
        print(f"モデル '{model_name}' のロードに失敗しました。デフォルトにフォールバックします: {e}")
        midi = mapp.transcribe(audio_path)

    midi.write(midi_path)
    return midi_path


def midi_to_tab_data(midi_path, transpose=0, capo=0):
    if not midi_path or not os.path.exists(midi_path): return []

    pm = pretty_midi.PrettyMIDI(midi_path)
    tab_data = []
    capo_strings = [s + capo for s in GUITAR_STRINGS]

    for instrument in pm.instruments:
        for note in instrument.notes:
            if note.end - note.start < 0.05: continue  # 短すぎる音はノイズとして除外

            time_key = round(note.start * 8) / 8
            pitch = note.pitch + transpose

            # 太い弦（6弦側）から順に候補を探し、最初に見つかった弦・フレットを採用する
            for i in range(5, -1, -1):
                string_pitch = capo_strings[i]
                fret = pitch - string_pitch

                if 0 <= fret <= 20:
                    tab_data.append({
                        "time": time_key,
                        "string": i + 1,
                        "fret": fret,
                        "note": pitch
                    })
                    break

    tab_data.sort(key=lambda x: x["time"])
    return tab_data

def data_to_ascii_tab(tab_data, reverse_display=False, width_limit=80):
    if not tab_data: return "No Data"

    headers = ["e|", "B|", "G|", "D|", "A|", "E|"]
    if reverse_display:
        headers = headers[::-1]

    time_map = {}
    for d in tab_data:
        idx = int(round(d["time"] / 0.125))
        if idx not in time_map: time_map[idx] = []
        time_map[idx].append(d)

    if not time_map: return ""
    min_idx, max_idx = min(time_map.keys()), max(time_map.keys())

    full_rows = [""] * 6

    for i in range(min_idx, max_idx + 1):
        notes = time_map.get(i, [])
        col_width = 3

        column = [""] * 6
        for string_num in range(1, 7):
            target_notes = [n for n in notes if n["string"] == string_num]

            val = "-" * col_width
            if target_notes:
                val = str(target_notes[-1]["fret"]).center(col_width, "-")

            row_idx = 6 - string_num if reverse_display else string_num - 1
            column[row_idx] = val

        for r in range(6):
            full_rows[r] += column[r] + "-"

    formatted_output = ""
    total_len = len(full_rows[0])

    for start in range(0, total_len, width_limit):
        end = start + width_limit
        for r in range(6):
            segment = full_rows[r][start:end]
            formatted_output += headers[r] + segment + "\n"
        formatted_output += "\n"

    return formatted_output

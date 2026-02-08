import os
import subprocess
import glob
import sys
import pretty_midi

# Omnizartの機能をインポート
# Omnizartの機能をインポート
from omnizart.music import app as mapp

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

GUITAR_STRINGS = [40, 45, 50, 55, 59, 64] 

def separate_audio(input_path):
    print("--- Demucsで分離中 ---")
    command = [sys.executable, "-m", "demucs", "-n", "htdemucs_6s", "--two-stems", "guitar", "-o", OUTPUT_DIR, input_path]
    subprocess.run(command, check=True)
    
    filename = os.path.splitext(os.path.basename(input_path))[0]
    search_path = os.path.join(OUTPUT_DIR, "htdemucs_6s", filename, "guitar.wav")
    if os.path.exists(search_path): return search_path
    
    found_all = glob.glob(os.path.join(OUTPUT_DIR, "**", "guitar.wav"), recursive=True)
    if found_all: return found_all[-1]
    raise FileNotFoundError("ギター音源が見つかりませんでした")

def audio_to_midi(audio_path, model_name="music-guitar-v1"):
    print(f"--- Omnizartで解析中 (Model: {model_name}) ---")
    output_midi_dir = os.path.join(OUTPUT_DIR, "midi")
    os.makedirs(output_midi_dir, exist_ok=True)
    
    filename = os.path.splitext(os.path.basename(audio_path))[0]
    midi_path = os.path.join(output_midi_dir, f"{filename}_omnizart.mid")
    
    try:
        midi = mapp.transcribe(audio_path, model_path="music-guitar-v1")
    except:
        midi = mapp.transcribe(audio_path)

    midi.write(midi_path)
    return midi_path

def midi_to_tab_data(midi_path, transpose=0, capo=0):
    """ V0: シンプルロジック """
    if not midi_path or not os.path.exists(midi_path): return []

    pm = pretty_midi.PrettyMIDI(midi_path)
    tab_data = []
    capo_strings = [s + capo for s in GUITAR_STRINGS]

    for instrument in pm.instruments:
        for note in instrument.notes:
            if note.end - note.start < 0.05: continue 
            
            time_key = round(note.start * 8) / 8 
            pitch = note.pitch + transpose
            
            assigned = False
            # 6弦(太い) -> 1弦(細い) の順でチェック
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
                    assigned = True
                    break 
            
    tab_data.sort(key=lambda x: x["time"])
    return tab_data

def data_to_ascii_tab(tab_data, reverse_display=False, width_limit=80):
    """ 
    TAB譜描画 (改良版)
    - reverse_display: Trueなら上下を反転(6弦を上にする)
    - width_limit: 指定文字数で改行する
    """
    if not tab_data: return "No Data"
    
    # 通常の並び: 1弦(e) 〜 6弦(E)
    headers = ["e|", "B|", "G|", "D|", "A|", "E|"]
    
    # 表示反転ならヘッダーも入れ替え
    if reverse_display:
        headers = headers[::-1]
    
    time_map = {}
    for d in tab_data:
        idx = int(round(d["time"] / 0.125))
        if idx not in time_map: time_map[idx] = []
        time_map[idx].append(d)
        
    if not time_map: return ""
    min_idx, max_idx = min(time_map.keys()), max(time_map.keys())
    
    # 全データを長い1本の文字列バッファに変換
    full_rows = [""] * 6
    
    for i in range(min_idx, max_idx + 1):
        notes = time_map.get(i, [])
        col_width = 3
        
        column = [""] * 6
        for string_num in range(1, 7):
            # string_numは常に 1=e, 6=E
            target_notes = [n for n in notes if n["string"] == string_num]
            
            val = "-" * col_width
            if target_notes:
                val = str(target_notes[-1]["fret"]).center(col_width, "-")
            
            # 格納場所を決める
            if reverse_display:
                # 弦1(index0) を 一番下(row5)へ
                # 弦6(index5) を 一番上(row0)へ
                row_idx = 6 - string_num
            else:
                # 弦1(index0) を 一番上(row0)へ
                row_idx = string_num - 1
            
            column[row_idx] = val

        for r in range(6):
            full_rows[r] += column[r] + "-"

    # --- 改行処理 (ここが新機能) ---
    formatted_output = ""
    total_len = len(full_rows[0])
    
    # width_limit文字ごとに区切って表示
    for start in range(0, total_len, width_limit):
        end = start + width_limit
        
        # 1ブロック分を作成
        for r in range(6):
            segment = full_rows[r][start:end]
            formatted_output += headers[r] + segment + "\n"
        
        formatted_output += "\n" # ブロック間の空行

    return formatted_output
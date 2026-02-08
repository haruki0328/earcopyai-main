import os
import subprocess
import glob
import sys
import pretty_midi
from basic_pitch.inference import predict_and_save

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 0=Low E (40) ... 5=High e (64)
GUITAR_STRINGS = [40, 45, 50, 55, 59, 64] 

def separate_audio(input_path):
    print("--- Demucsで分離中 ---")
    # Demucsを実行
    command = [sys.executable, "-m", "demucs", "-n", "htdemucs_6s", "--two-stems", "guitar", "-o", OUTPUT_DIR, input_path]
    subprocess.run(command, check=True)
    
    # 出力されたファイルを探す
    filename = os.path.splitext(os.path.basename(input_path))[0]
    
    # 1. 予想されるパスをチェック
    search_path = os.path.join(OUTPUT_DIR, "htdemucs_6s", filename, "guitar.wav")
    if os.path.exists(search_path): 
        return search_path
    
    # 2. 見つからない場合は再帰的に検索
    found_all = glob.glob(os.path.join(OUTPUT_DIR, "**", "guitar.wav"), recursive=True)
    
    # 直近で作られたものを返す（念のため）
    if found_all: 
        return max(found_all, key=os.path.getctime)
        
    raise FileNotFoundError("ギター音源が見つかりませんでした")

def audio_to_midi(audio_path):
    """ Basic Pitchを使ってMIDI変換 """
    print(f"--- Basic Pitchで解析中 ---")
    
    output_midi_dir = os.path.join(OUTPUT_DIR, "midi")
    os.makedirs(output_midi_dir, exist_ok=True)
    
    # Basic Pitchの推論実行
    # save_midi=True にすると、自動的に MIDIファイルが保存されます
    predict_and_save(
        [audio_path],
        output_directory=output_midi_dir,
        save_midi=True,
        sonify_midi=False,
        save_model_outputs=False,
        save_notes=False
    )
    
    # Basic Pitchは元のファイル名に "_basic_pitch.mid" を付与して保存する仕様
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    midi_path = os.path.join(output_midi_dir, f"{base_name}_basic_pitch.mid")
    
    if not os.path.exists(midi_path):
        raise FileNotFoundError(f"MIDIファイルの生成に失敗しました: {midi_path}")

    return midi_path

def midi_to_tab_data(midi_path, transpose=0, capo=0):
    """ MIDIノートをギターのフレット位置に変換する """
    if not midi_path or not os.path.exists(midi_path): return []

    pm = pretty_midi.PrettyMIDI(midi_path)
    tab_data = []
    
    # カポを考慮した開放弦の音程 (カポ2なら全弦+2)
    # 実際には「カポの分だけ音程を下げて、0フレット=カポ位置」として計算する
    # string_pitch は「その弦の0フレット(開放)のMIDIノート番号」
    capo_strings = [s + capo for s in GUITAR_STRINGS]

    for instrument in pm.instruments:
        for note in instrument.notes:
            # 極端に短いノイズのような音は無視
            if note.end - note.start < 0.05: continue 
            
            # 16分音符刻み(0.125秒単位とは限らないが簡易的に量子化)
            time_key = round(note.start * 8) / 8 
            
            # トランスポーズ適用
            pitch = note.pitch + transpose
            
            # 最適な弦を選ぶロジック
            # 高い弦(1弦: index 5)から低い弦(6弦: index 0)の順にチェックして、
            # 最初に「弾ける範囲(0-20フレット)」に収まった場所を採用する
            # これにより「ローコード（開放弦に近い位置）」が優先される
            
            best_position = None
            
            # index 5 (High e) -> index 0 (Low E)
            for string_idx in range(5, -1, -1): 
                open_string_pitch = capo_strings[string_idx]
                fret = pitch - open_string_pitch
                
                if 0 <= fret <= 22: # 22フレットまで許容
                    # string_idx: 0=LowE, 5=HighE
                    # 表示用に 1=HighE ... 6=LowE に変換するか、データとしては
                    # そのまま物理的な弦番号(1=LowE 〜 6=HighE)で持つか。
                    # ここでは物理的な弦インデックス(1始まり)を保存します。
                    # 1=Low E, 6=High e
                    tab_data.append({
                        "time": time_key,
                        "string_idx": string_idx, # 0-5
                        "fret": fret,
                        "note": pitch
                    })
                    best_position = True
                    break 
            
    # 時間順にソート
    tab_data.sort(key=lambda x: x["time"])
    return tab_data

def data_to_ascii_tab(tab_data, reverse_display=False, width_limit=80):
    """ TAB譜を文字列として生成 """
    if not tab_data: return "No Data Generated."
    
    # ヘッダー定義
    # 通常: 上が1弦(e), 下が6弦(E)
    # headers[0] が一番上の行になる
    headers = ["e|", "B|", "G|", "D|", "A|", "E|"]
    
    # reverse_display=Trueなら、上が6弦(E), 下が1弦(e)
    if reverse_display:
        headers = ["E|", "A|", "D|", "G|", "B|", "e|"]
    
    # 時間ごとにデータをまとめる
    time_map = {}
    for d in tab_data:
        # 時間をキーにして辞書にまとめる
        t = d["time"]
        if t not in time_map: time_map[t] = []
        time_map[t].append(d)
        
    if not time_map: return ""
    
    # 時間順にキーを取得
    sorted_times = sorted(time_map.keys())
    
    # 各行の文字列バッファを作成
    full_rows = [""] * 6
    
    # 全タイムステップを処理
    for t in sorted_times:
        notes = time_map[t]
        col_width = 3 # 1列の幅
        
        # このタイミングでの各弦の表示文字を作成
        column_chars = ["-"] * 6 # デフォルトは "-"
        
        for note_info in notes:
            # note_info["string_idx"] は 0(Low E) 〜 5(High e)
            s_idx = note_info["string_idx"]
            fret_str = str(note_info["fret"])
            
            # 表示行の決定
            # 通常表示(High eが上): 
            #   High e (idx 5) -> row 0
            #   Low E  (idx 0) -> row 5
            #   row = 5 - s_idx
            
            if reverse_display:
                # 反転表示(Low Eが上):
                #   Low E (idx 0) -> row 0
                row = s_idx
            else:
                row = 5 - s_idx
            
            column_chars[row] = fret_str
            
        # バッファに追加
        for r in range(6):
            # 中央寄せで追加
            full_rows[r] += column_chars[r].center(col_width, "-") + "-"

    # --- 改行処理 ---
    formatted_output = ""
    total_len = len(full_rows[0])
    
    for start in range(0, total_len, width_limit):
        end = start + width_limit
        
        # ヘッダー + 譜面データ + 改行
        for r in range(6):
            segment = full_rows[r][start:end]
            formatted_output += headers[r] + segment + "\n"
        
        formatted_output += "\n" # ブロック間の空行

    return formatted_output
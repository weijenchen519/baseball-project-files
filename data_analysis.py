import os
import json
import pandas as pd
from pathlib import Path
import sqlite3
from datetime import datetime

class CPBLDataProcessor:
    """CPBL資料處理器 - 提供多種輸出格式"""
    
    def __init__(self, input_folder, output_folder):
        self.input_folder = input_folder
        self.output_folder = output_folder
        Path(output_folder).mkdir(exist_ok=True)
    
    def load_json_data(self, file_path):
        """載入JSON資料"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 檢查資料格式
            if isinstance(data, list):
                print(f"警告: {file_path} 包含陣列格式，跳過處理")
                return None
            return data
    
    def extract_basic_info(self, data):
        """提取基本比賽資訊"""
        return {
            'seasonId': data.get('seasonId'),
            'season': data.get('season'),
            'seq': data.get('seq'),
            'date': data.get('date'),
            'stadium': data.get('stadium'),
            'awayTeamId': data.get('awayTeamId'),
            'awayTeam': data.get('awayTeam'),
            'awayScores': str(data.get('awayScores')) if isinstance(data.get('awayScores'), list) else data.get('awayScores'),
            'homeTeamId': data.get('homeTeamId'),
            'homeTeam': data.get('homeTeam'),
            'homeScores': str(data.get('homeScores')) if isinstance(data.get('homeScores'), list) else data.get('homeScores')
        }
    
    def extract_player_stats(self, data, team_type):
        """提取球員統計資料"""
        batter_box = data.get(f'{team_type}BatterBox', [])
        pitcher_box = data.get(f'{team_type}PitcherBox', [])
        
        players = []
        
        # 處理打擊資料
        for player in batter_box:
            player_data = {
                'team_type': team_type,
                'player_type': 'batter',
                'order': player.get('order'),
                'playerId': player.get('playerId'),
                'playerNumber': player.get('playerNumber'),
                'playerName': player.get('playerName'),
                'PA': player.get('PA'),
                'AB': player.get('AB'),
                'R': player.get('R'),
                'H': player.get('H'),
                'RBI': player.get('RBI'),
                '2B': player.get('2B'),
                '3B': player.get('3B'),
                'HR': player.get('HR'),
                'BB': player.get('BB'),
                'SO': player.get('SO'),
                'SB': player.get('SB'),
                'CS': player.get('CS')
            }
            players.append(player_data)
        
        # 處理投手資料
        for player in pitcher_box:
            player_data = {
                'team_type': team_type,
                'player_type': 'pitcher',
                'order': player.get('order'),
                'playerId': player.get('playerId'),
                'playerNumber': player.get('playerNumber'),
                'playerName': player.get('playerName'),
                'IPOuts': player.get('IPOuts'),
                'NP': player.get('NP'),
                'BF': player.get('BF'),
                'H': player.get('H'),
                'HR': player.get('HR'),
                'BB': player.get('BB'),
                'SO': player.get('SO'),
                'R': player.get('R'),
                'ER': player.get('ER')
            }
            players.append(player_data)
        
        return players
    
    def extract_pa_records(self, data, team_type):
        """提取打席記錄"""
        pa_list = data.get(f'{team_type}PAList', [])
        records = []
        
        for pa in pa_list:
            pa_data = {
                'team_type': team_type,
                'inning': pa.get('inning'),
                'scored': pa.get('scored'),
                'batterName': pa.get('batterName'),
                'batterHand': pa.get('batterHand'),
                'pitcherName': pa.get('pitcherName'),
                'pitcherHand': pa.get('pitcherHand'),
                'paRound': pa.get('paRound'),
                'paOrder': pa.get('paOrder'),
                'isPH': pa.get('isPH'),
                'awayScores': pa.get('awayScores'),
                'homeScores': pa.get('homeScores'),
                'strikes': pa.get('strikes'),
                'balls': pa.get('balls'),
                'outs': pa.get('outs'),
                'bases': pa.get('bases'),
                'result': pa.get('result'),
                'RBI': pa.get('RBI'),
                'locationCode': pa.get('locationCode'),
                'trajectory': pa.get('trajectory'),
                'hardness': pa.get('hardness')
            }
            records.append(pa_data)
        
        return records
    
    def create_normalized_csvs(self, data, game_id):
        """創建標準化的CSV檔案"""
        # 基本比賽資訊
        basic_info = self.extract_basic_info(data)
        basic_df = pd.DataFrame([basic_info])
        basic_df.to_csv(f'{self.output_folder}/{game_id}_basic_info.csv', index=False, encoding='utf-8-sig')
        
        # 球員統計
        away_players = self.extract_player_stats(data, 'away')
        home_players = self.extract_player_stats(data, 'home')
        all_players = away_players + home_players
        players_df = pd.DataFrame(all_players)
        players_df.to_csv(f'{self.output_folder}/{game_id}_player_stats.csv', index=False, encoding='utf-8-sig')
        
        # 打席記錄
        away_pas = self.extract_pa_records(data, 'away')
        home_pas = self.extract_pa_records(data, 'home')
        all_pas = away_pas + home_pas
        pas_df = pd.DataFrame(all_pas)
        pas_df.to_csv(f'{self.output_folder}/{game_id}_pa_records.csv', index=False, encoding='utf-8-sig')
        
        return {
            'basic_info': basic_df,
            'player_stats': players_df,
            'pa_records': pas_df
        }
    
    def create_sqlite_database(self, all_data):
        """創建SQLite資料庫"""
        db_path = f'{self.output_folder}/cpbl_2024.db'
        conn = sqlite3.connect(db_path)
        
        # 創建基本比賽資訊表
        basic_info_list = []
        for game_id, data in all_data.items():
            if data is not None:  # 跳過無效資料
                basic_info = self.extract_basic_info(data)
                basic_info['game_id'] = game_id
                basic_info_list.append(basic_info)
        
        basic_df = pd.DataFrame(basic_info_list)
        basic_df.to_sql('games', conn, if_exists='replace', index=False)
        
        # 創建球員統計表
        all_players = []
        for game_id, data in all_data.items():
            if data is not None:  # 跳過無效資料
                away_players = self.extract_player_stats(data, 'away')
                home_players = self.extract_player_stats(data, 'home')
                for player in away_players + home_players:
                    player['game_id'] = game_id
                    all_players.append(player)
        
        players_df = pd.DataFrame(all_players)
        players_df.to_sql('player_stats', conn, if_exists='replace', index=False)
        
        # 創建打席記錄表
        all_pas = []
        for game_id, data in all_data.items():
            if data is not None:  # 跳過無效資料
                away_pas = self.extract_pa_records(data, 'away')
                home_pas = self.extract_pa_records(data, 'home')
                for pa in away_pas + home_pas:
                    pa['game_id'] = game_id
                    all_pas.append(pa)
        
        pas_df = pd.DataFrame(all_pas)
        pas_df.to_sql('pa_records', conn, if_exists='replace', index=False)
        
        conn.close()
        return db_path
    
    def process_all_files(self):
        """處理所有檔案"""
        json_files = [f for f in os.listdir(self.input_folder) if f.endswith('.json')]
        
        print(f"開始處理 {len(json_files)} 個JSON檔案...")
        
        all_data = {}
        
        for i, json_file in enumerate(json_files, 1):
            try:
                print(f"[{i}/{len(json_files)}] 處理: {json_file}")
                
                file_path = os.path.join(self.input_folder, json_file)
                data = self.load_json_data(file_path)
                
                if data is None:  # 跳過無效資料
                    continue
                
                game_id = json_file.replace('.json', '')
                all_data[game_id] = data
                
                # 創建標準化CSV
                self.create_normalized_csvs(data, game_id)
                
            except Exception as e:
                print(f"處理 {json_file} 時發生錯誤: {str(e)}")
                continue
        
        # 創建SQLite資料庫
        print("創建SQLite資料庫...")
        db_path = self.create_sqlite_database(all_data)
        
        print(f"處理完成！")
        print(f"輸出資料夾: {self.output_folder}")
        print(f"SQLite資料庫: {db_path}")
        
        return all_data

def main():
    """主程式"""
    input_folder = "CPBL-2024-OpenData"
    output_folder = "CPBL-2024-Processed"
    
    processor = CPBLDataProcessor(input_folder, output_folder)
    all_data = processor.process_all_files()
    
    # 顯示統計資訊
    print("\n" + "="*50)
    print("資料處理統計")
    print("="*50)
    print(f"總比賽場數: {len([d for d in all_data.values() if d is not None])}")
    
    # 計算總打席數
    total_pas = 0
    for game_id, data in all_data.items():
        if data is not None:  # 跳過無效資料
            away_pas = len(data.get('awayPAList', []))
            home_pas = len(data.get('homePAList', []))
            total_pas += away_pas + home_pas
    
    print(f"總打席數: {total_pas}")
    
    # 計算總球員數
    total_players = 0
    for game_id, data in all_data.items():
        if data is not None:  # 跳過無效資料
            away_batters = len(data.get('awayBatterBox', []))
            away_pitchers = len(data.get('awayPitcherBox', []))
            home_batters = len(data.get('homeBatterBox', []))
            home_pitchers = len(data.get('homePitcherBox', []))
            total_players += away_batters + away_pitchers + home_batters + home_pitchers
    
    print(f"總球員數: {total_players}")

if __name__ == "__main__":
    main()

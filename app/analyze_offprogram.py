import pandas as pd
import os

def analyze_offprogram_structure():
    """Анализирует структуру файла OffProgram-good.xlsx"""
    
    file_path = 'data/OffProgram-good.xlsx'
    
    if not os.path.exists(file_path):
        print(f"Файл {file_path} не найден!")
        return
    
    try:
        # Читаем Excel файл
        df = pd.read_excel(file_path)
        
        print("=== АНАЛИЗ СТРУКТУРЫ OFF PROGRAM ===")
        print(f"Размер данных: {df.shape[0]} строк, {df.shape[1]} колонок")
        print("\nКолонки:")
        for i, col in enumerate(df.columns):
            print(f"  {i+1}. {col}")
        
        print("\nПервые 5 строк:")
        print(df.head())
        
        print("\nТипы данных:")
        print(df.dtypes)
        
        print("\nСтатистика по числовым колонкам:")
        print(df.describe())
        
        print("\nПроверка на пустые значения:")
        print(df.isnull().sum())
        
        # Показываем уникальные значения для каждой колонки (первые 10)
        print("\nУникальные значения (первые 10):")
        for col in df.columns:
            unique_vals = df[col].dropna().unique()
            print(f"\n{col}:")
            if len(unique_vals) <= 10:
                print(f"  {unique_vals}")
            else:
                print(f"  {unique_vals[:10]}... (всего {len(unique_vals)})")
                
    except Exception as e:
        print(f"Ошибка при чтении файла: {e}")

if __name__ == "__main__":
    analyze_offprogram_structure() 
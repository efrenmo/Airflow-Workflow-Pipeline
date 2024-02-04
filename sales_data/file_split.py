# generate separate sales csv files for each date
import pandas as pd

csv_file_path = 'sales.csv'

df = pd.read_csv(csv_file_path)

date_column = 'TRANS_DT'

# unique_dates = df[date_column].unique()
unique_dates=['2024-01-01','2024-01-02','2024-01-03','2024-01-04','2024-01-05']

for unique_date in unique_dates:

    filtered_df = df[df[date_column] == unique_date]


    output_file_path = f'sales_{unique_date}.csv'
    filtered_df.to_csv(output_file_path, index=False)

    print(f"CSV file for {unique_date} has been created: {output_file_path}")

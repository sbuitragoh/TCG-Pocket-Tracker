from src.GUI import DataFrameViewer
from src import importer

if __name__ == "__main__":
    df = importer.read_json_file()
    df = importer.clean_db(df)
    app = DataFrameViewer(df)
    app.mainloop()

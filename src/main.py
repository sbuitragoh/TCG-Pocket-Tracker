from src.gui import CollectionViewer
from src import importer
import asyncio

async def main():
	df = importer.read_json_file()
	df = importer.clean_db(df)
	app = CollectionViewer(df)
	app.mainloop()

if __name__ == '__main__':
	asyncio.run(main())
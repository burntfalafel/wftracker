# Wftracker

Pretty easy to use program to quickly open a page from the Warframe Wiki.
First you're going to be asked for the item category, after that you're asked for the starting letter of your item, then you just have to choose your desired item from a numbered list et voilà, wiki page opens.

### Update resources/
To update the resources folder to the latest warframe wiki data, run the following command:
```bash
python update_resources.py
```

### Frontend tracker
To run the frontend tracker, run the following command:
```bash
python3 flask_app.py
```
Then open your browser and go to [http://locahost:5000](http://localhost:5000).
All data is saved when you click the "Save Progress" button. Do not forget to press it :).

### Screenshot
![Screenshot](screenshot.png)

### Credits
- [WfWikiFinder](https://github.com/umpanz/WfWikiFinder) for initial inspiration



# djangovue
![Vue.js Logo](https://github.com/mikebz/djangovue/raw/master/frontend/img/logo.png "Vue.js")

This is a starter project for Django with Vue.js.  I fell in love with the readability you get in Vue.js and 
decided to create a project where all components are laid out in the most readable way.

Note that this doesn't have features like hot reloading for webpack, but it's a good webpack starting point to build on.

## How to get started?
1. Get a copy of the repo on your machine
```
git clone https://github.com/mikebz/djangovue.git
cd djangovue
```

2. Set up virtual environment
```
python3 -m venv venv
source venv/bin/activate
```

3. Install the necessary libraries.
```
pip install -r requirements.txt
npm install
```

4. Build the Vue.js front end.
```
npm run build
```

5. Run the Django project
```
python3 manage.py runserver
```

At this point in time you should be able to navigate to your localhost:8000 and see a template rendered.  You can also run
the `npm run watch` in a separate window if you want to rebuild your frontend.  Note that for simplicity there is no hot
reloading so you would need to refresh the page when you save your front end files.

## Sources
This only worked because people before me created some wonderful examples.
- https://github.com/djstein/vue-django-webpack
- https://github.com/ezhome/django-webpack-loader

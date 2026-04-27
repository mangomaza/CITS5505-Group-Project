# Mix It Up

## Team Members
| UWA ID | Name | GitHub Username |
|:--------:|:------------:|:-----------:|
| 21211711 | Asad Maza | mangomaza |
| 24923772 | Jianing Chen | Ricky101087 |
| 24563207 | Wendy Song | WendySong1 |
| 24489475 | Wenmin Luo | onikirinana |

## Project Description

Mix It Up is a web app for creating, logging, and sharing cocktail and food recipes with friends. Users can browse community recipes, rate what others have made, and use a random recipe generator when they're not sure what to try next. The idea is to keep it simple and social, so you can share your creations with specific people and see what they think.

## Contributing

All work happens on feature branches off main. Open a pull request when your feature or fix is ready, and it needs at least one review before merging. Keep commits small and meaningful, and reference the relevant issue in your PR where it makes sense.

For the full workflow, including branch naming, commit messages, and the PR process, see the [Git Contribution Guide](docs/git-contribution-guide.md).

## Project Features

The app lets users sign up, log in, and manage their own recipe collection. You can create, edit, and delete your recipes, and choose to share them with specific friends rather than making everything public. There's a rating system so people can give feedback on shared recipes, and a random recipe generator that pulls from the community pool when you want something new. The whole thing is responsive so it works on both desktop and mobile.

## Design and Development

The frontend uses Bootstrap 5 for layout and responsiveness, with custom CSS on top for styling. Development is split across feature branches and tracked through GitHub issues.

## Technology Stack

**Backend:** Python, Flask

**Frontend:** HTML5, CSS3, Bootstrap 5, JavaScript, jQuery

**Database:** SQLite

## Setup

1. Clone the repo and change into the project folder.

   ```
   git clone https://github.com/mangomaza/CITS5505-Group-Project.git
   cd CITS5505-Group-Project
   ```

2. Create and activate a virtual environment.

   Windows:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   ```

   macOS/Linux:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies.

   ```
   pip install -r requirements.txt
   ```

## Running the App

With your virtual environment activated, run:

```
python manage.py
```

Then open http://127.0.0.1:5000 in your browser.

By default the app uses the development config. To change it, set `FLASK_CONFIG` before running (`development`, `testing`, or `production`).

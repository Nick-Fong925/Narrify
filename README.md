# Reddit AITA YouTube App

This project is a full-stack application designed to scrape the "Am I The Asshole" subreddit, process the content for safety and quality, and prepare it for YouTube video generation. It consists of a backend built with TypeScript and Express, and a frontend built with React.

## Project Structure

```
reddit-aita-youtube-app
├── backend
│   ├── src
│   │   ├── app.ts
│   │   ├── controllers
│   │   │   └── redditController.ts
│   │   ├── routes
│   │   │   └── redditRoutes.ts
│   │   ├── services
│   │   │   ├── scraperService.ts
│   │   │   ├── contentProcessor.ts
│   │   │   └── videoPrepService.ts
│   │   ├── utils
│   │   │   └── index.ts
│   │   └── types
│   │       └── index.ts
│   ├── package.json
│   ├── tsconfig.json
│   └── README.md
├── frontend
│   ├── src
│   │   ├── App.tsx
│   │   ├── components
│   │   │   └── RedditPostList.tsx
│   │   ├── pages
│   │   │   └── Home.tsx
│   │   ├── services
│   │   │   └── api.ts
│   │   └── types
│   │       └── index.ts
│   ├── package.json
│   ├── tsconfig.json
│   └── README.md
├── .gitignore
└── README.md
```

## Backend

The backend is responsible for scraping Reddit posts, processing the content, and providing an API for the frontend to consume.

### Setup

1. Navigate to the `backend` directory.
2. Install dependencies:
   ```
   npm install
   ```
3. Run the application:
   ```
   npm start
   ```

### API Endpoints

- `GET /api/reddit/posts`: Fetches scraped Reddit posts.
- `POST /api/reddit/process`: Processes the scraped content for safety and quality.

## Frontend

The frontend is a React application that displays the scraped Reddit posts and allows users to interact with the content.

### Setup

1. Navigate to the `frontend` directory.
2. Install dependencies:
   ```
   npm install
   ```
3. Run the application:
   ```
   npm start
   ```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./
RUN npm ci

# Copy source code
COPY . .

# Build the Next.js app
RUN npm run build

EXPOSE 3000

# Start the application
CMD ["npm", "start"]

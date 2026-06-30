FROM node:18-alpine
WORKDIR /app

# Install dependencies for building
RUN apk add --no-cache curl bash git

# Install pnpm globally
RUN curl -fsSL https://get.pnpm.io/install-pnpm.sh | bash -s -- --yes
ENV PATH=/root/.pnpm/global/bin:$PATH

# Copy package files
COPY frontend/package*.json ./
RUN pnpm install --frozen-lockfile

# Copy application source
COPY frontend/ .

# Build the application
RUN pnpm run build

# Install serve for production
RUN npm install -g serve

EXPOSE 5173
CMD ["serve", "-s", "dist", "-l", "5173"]

# Load visualization library
library(ggplot2)
library(magrittr)
library(dplyr)
library(Matrix)
spotify_processed <-arrow::read_parquet("./data/spotify_processed.parquet")

# 1. Build a Multiple Linear Regression Model
# Predicting popularity based on danceability, energy, and valence (positivity)
popularity_model <- lm(popularity ~ danceability + energy + valence + loudness, data = spotify_processed)

# 2. View the statistical summary
# Look at the 'Pr(>|t|)' column (p-values) to see which features are statistically significant
summary(popularity_model)

# 3. Visualize the relationship (Example: Danceability vs Popularity)
# Using a sample to avoid overplotting (10,000 random rows)
sample_data <- spotify_processed %>% sample_n(10000)

ggplot(sample_data, aes(x = danceability, y = popularity)) +
  geom_point(alpha = 0.1, color = "blue") +
  geom_smooth(method = "lm", color = "red") +
  theme_minimal() +
  labs(title = "Impact of Danceability on Track Popularity",
       x = "Danceability Score",
       y = "Popularity")


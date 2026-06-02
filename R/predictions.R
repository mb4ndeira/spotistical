# =====================================================================
# SPOTIFY PREDICTIVE MODELING: POPULARITY & ARTIST IDENTIFICATION
# =====================================================================

# Install necessary packages if you don't have them
# install.packages(c("tidyverse", "ranger", "caret", "vip"))

library(tidyverse)
library(ranger)   # Fast implementation of Random Forests
library(caret)    # For data partitioning
library(vip)      # For visualizing variable importance

#' 1. Data Preparation & Sampling
#' 2.1 Million rows is very large for local ML. We will sample it.
#' @param df The spotify_processed dataframe
prepare_ml_data <- function(df) {
  cat("Preparing data...\n")

  # Select only the potential predictor features and our two targets
  ml_data <- df %>%
    select(popularity, artists, is_explicit, duration_ms, danceability,
           energy, key, loudness, mode, speechiness, acousticness,
           instrumentalness, liveness, valence, tempo, daily_movement) %>%
    # Convert explicit flag to numeric/factor
    mutate(is_explicit = as.factor(is_explicit)) %>%
    drop_na()

  return(ml_data)
}

#' 2. Analyze Predictors for POPULARITY (Regression)
#' @param data The cleaned dataset
analyze_popularity <- function(data) {
  cat("\n--- RUNNING POPULARITY ANALYSIS ---\n")

  # Sample 100,000 rows for computational efficiency
  set.seed(123)
  pop_data <- data %>% sample_n(min(100000, nrow(data)))

  # Remove 'artists' as we are just looking at audio/track features for this
  pop_data <- pop_data %>% select(-artists)

  # Train a Random Forest model using the 'ranger' package
  # 'impurity' gives us the variance reduction (importance) of each variable
  pop_model <- ranger(
    popularity ~ .,
    data = pop_data,
    num.trees = 200,
    importance = 'impurity',
    seed = 123
  )

  cat("Model R-Squared (OOB):", round(pop_model$r.squared, 4), "\n")

  # Plot variable importance
  p <- vip(pop_model, num_features = 15, geom = "col",
           aesthetics = list(fill = "steelblue")) +
    theme_minimal() +
    labs(title = "Feature Importance: Predicting Track Popularity",
         subtitle = "Based on Variance Reduction in Random Forest")
  print(p)

  return(pop_model)
}

#' 3. Analyze Predictors for ARTISTS (Multi-class Classification)
#' @param data The cleaned dataset
analyze_artists <- function(data) {
  cat("\n--- RUNNING ARTIST SIGNATURE ANALYSIS ---\n")

  # Predicting 13k artists is computationally unfeasible and statistically noisy.
  # We will filter the dataset to only include the Top 20 most frequent artists.
  top_artists <- data %>%
    count(artists, sort = TRUE) %>%
    slice(1:20) %>%
    pull(artists)

  artist_data <- data %>%
    filter(artists %in% top_artists) %>%
    # Drop unused factor levels
    mutate(artists = droplevels(artists)) %>%
    # Remove popularity as a predictor (we want to predict based on sound)
    select(-popularity)

  # Sample down if the top 20 still have hundreds of thousands of rows
  set.seed(456)
  if(nrow(artist_data) > 100000) {
    artist_data <- artist_data %>% sample_n(100000)
  }

  # Train Random Forest Classification Model
  # 'impurity' here measures Gini index decrease
  artist_model <- ranger(
    artists ~ .,
    data = artist_data,
    num.trees = 200,
    importance = 'impurity',
    classification = TRUE,
    seed = 456
  )

  # Calculate rough accuracy based on Out-Of-Bag Error
  accuracy <- 1 - artist_model$prediction.error
  cat("Model Accuracy for Top 20 Artists:", round(accuracy * 100, 2), "%\n")

  # Plot variable importance
  p2 <- vip(artist_model, num_features = 15, geom = "col",
            aesthetics = list(fill = "darkred")) +
    theme_minimal() +
    labs(title = "Feature Importance: Distinguishing Top 20 Artists",
         subtitle = "Which audio features act as the strongest 'Audio Signatures'?")
  print(p2)

  return(artist_model)
}

#' Master Execution Function
run_advanced_models <- function(df) {
  # 1. Clean and prep
  prepared_data <- prepare_ml_data(df)

  # 2. Popularity Drivers
  popularity_results <- analyze_popularity(prepared_data)

  # 3. Artist Audio Signatures
  artist_results <- analyze_artists(prepared_data)

  cat("\nAnalyses complete. Check your plot pane for the Variable Importance charts.\n")
}

# =====================================================================
# EXECUTE THE PIPELINE
# =====================================================================
# Assuming your dataframe is loaded as 'spotify_processed'
run_advanced_models(spotify_processed)

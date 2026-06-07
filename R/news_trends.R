# =====================================================================
# MACRO TREND ANALYSIS: GLOBAL NEWS SENTIMENT VS. DAILY AUDIO FEATURES
# =====================================================================

library(tidyverse)
library(tidytext)
library(lubridate)

#' 1. Aggregate Spotify Data to Find the "Daily Global Mood"
#' @param df The spotify_processed dataframe
aggregate_daily_audio_trends <- function(df) {
  cat("Aggregating daily audio fingerprints...\n")

  daily_trends <- df %>%
    group_by(snapshot_date) %>%
    summarise(
      # We calculate the mean of emotional/physical audio features for the day
      avg_valence = mean(valence, na.rm = TRUE),           # Musical positivity
      avg_energy = mean(energy, na.rm = TRUE),             # Intensity and activity
      avg_danceability = mean(danceability, na.rm = TRUE), # Club/rhythm friendly
      avg_acousticness = mean(acousticness, na.rm = TRUE), # Often correlates with sad/calm
      total_streams_or_tracks = n()
    ) %>%
    arrange(snapshot_date)

  return(daily_trends)
}

#' 2. Fetch & Analyze Global Macro News (Mocked for demonstration)
#' In production, use the GDELT API or NewsAPI for top global headlines
#' @param start_date The start of your dataset
fetch_global_macro_news <- function(start_date) {
  cat("Fetching global macro news events...\n")

  # MOCK DATA: Simulating days with major global events
  # A real API would pull hundreds of headlines per day to average out the sentiment
  mock_macro_news <- tibble(
    snapshot_date = as.Date(c("2024-06-05", "2024-06-08", "2024-06-11", "2024-06-15")),
    global_event = c(
      "Global Market Crash & Economic Uncertainty",
      "Normal News Day",
      "World Cup Final & Global Celebrations",
      "Major Natural Disaster Reported"
    ),
    # Pre-calculated sentiment for the day (-1.0 to 1.0)
    global_sentiment_score = c(-0.85, 0.10, 0.90, -0.75)
  )

  return(mock_macro_news)
}

#' 3. Merge and Correlate the "World Mood" with "Listening Mood"
#' @param daily_audio_df The aggregated Spotify data
#' @param macro_news_df The daily global news sentiment
analyze_cultural_impact <- function(daily_audio_df, macro_news_df) {
  cat("Merging datasets and calculating cultural correlations...\n")

  # Join the datasets
  merged_trends <- daily_audio_df %>%
    left_join(macro_news_df, by = "snapshot_date") %>%
    # If no major news event, assume neutral sentiment (0)
    replace_na(list(global_sentiment_score = 0, global_event = "Routine News Cycle"))

  # Calculate Correlations (Does bad news = sad music?)
  # We test sentiment against Valence (happiness) and Acousticness (calmness/sadness)
  cor_valence <- cor(merged_trends$global_sentiment_score, merged_trends$avg_valence, use = "complete.obs")
  cor_acoustic <- cor(merged_trends$global_sentiment_score, merged_trends$avg_acousticness, use = "complete.obs")

  cat(sprintf("\n--- MACRO CORRELATIONS ---\n"))
  cat(sprintf("News Sentiment vs. Musical Valence (Positivity): %.3f\n", cor_valence))
  cat(sprintf("News Sentiment vs. Musical Acousticness: %.3f\n", cor_acoustic))

  return(merged_trends)
}

#' 4. Visualize the Trend Shifts
#' @param analysis_df The merged dataframe
plot_macro_trends <- function(analysis_df) {

  # We pivot the data to easily plot multiple audio features on one graph
  plot_data <- analysis_df %>%
    select(snapshot_date, avg_valence, avg_energy, avg_acousticness, global_sentiment_score, global_event) %>%
    pivot_longer(cols = starts_with("avg_"), names_to = "audio_feature", values_to = "value") %>%
    # Clean up names for the legend
    mutate(audio_feature = str_replace(audio_feature, "avg_", ""))

  # Identify major event days to highlight on the plot
  major_events <- analysis_df %>% filter(abs(global_sentiment_score) > 0.5)

  p <- ggplot() +
    # Plot the daily audio features as lines
    geom_line(data = plot_data, aes(x = snapshot_date, y = value, color = audio_feature), size = 1) +

    # Add vertical lines for major global events
    geom_vline(data = major_events, aes(xintercept = as.numeric(snapshot_date)),
               linetype = "dashed", color = "black", alpha = 0.5) +

    # Add text labels for the events
    geom_text(data = major_events, aes(x = snapshot_date, y = max(plot_data$value) * 1.05, label = global_event),
              angle = 45, hjust = 0, size = 3) +

    # Color mapping
    scale_color_brewer(palette = "Set1") +
    theme_minimal() +
    labs(
      title = "Do Global Events Shift Our Listening Habits?",
      subtitle = "Comparing average daily audio features against major news cycles",
      x = "Date",
      y = "Average Audio Feature Score",
      color = "Audio Feature"
    ) +
    theme(legend.position = "bottom")

  print(p)
}

#' Master Execution Function
run_macro_cultural_analysis <- function(spotify_data) {
  # 1. Get Daily Spotify Fingerprint
  daily_audio <- aggregate_daily_audio_trends(spotify_data)

  # 2. Get Global News Sentiment (Mocked here, replace with GDELT API in prod)
  start_date <- min(daily_audio$snapshot_date, na.rm = TRUE)
  global_news <- fetch_global_macro_news(start_date)

  # 3. Analyze Correlations
  cultural_data <- analyze_cultural_impact(daily_audio, global_news)

  # 4. Plot the shifts
  plot_macro_trends(cultural_data)
}

# =====================================================================
# EXECUTE THE PIPELINE
# =====================================================================
# run_macro_cultural_analysis(spotify_processed)

# join datasets by country and date

library(tidyverse)

# 1. Aggregate the 'chile' news dataset by date
chile_news_daily <- chile %>%
  group_by(data) %>%
  summarise(
    # Count how many articles were published that day
    total_articles = n(),

    # Combine all titles into a single text string separated by " | "
    titulos_do_dia = paste(titulo, collapse = " | "),

    # Combine all themes/tags into a single string
    temas_do_dia = paste(tema, collapse = " | ")
  )

# 2. Join the aggregated news to the Spotify dataset
spotify_news_joined <- chile_spotify %>%
  left_join(chile_news_daily, by = c("snapshot_date" = "data"))

# View the result
head(spotify_news_joined)

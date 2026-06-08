# =====================================================================
# EVENT STUDY: REAL-WORLD IMPACT ON SPOTIFY AUDIO FEATURES
# =====================================================================

# Install necessary packages if missing
# install.packages(c("tidyverse", "lubridate", "broom"))

library(tidyverse)
library(lubridate)
library(broom)

#' 1. Aggregate Spotify to Daily Global Baselines
#' @param spotify_df The massive 2.1M row dataframe
aggregate_daily_spotify <- function(spotify_df = spotify_processed) {
  cat("Calculating daily global audio baselines...\n")

  daily_baseline <- spotify_df %>%
    group_by(snapshot_date) %>%
    summarise(
      avg_valence = mean(valence, na.rm = TRUE),
      avg_energy = mean(energy, na.rm = TRUE),
      avg_danceability = mean(danceability, na.rm = TRUE),
      avg_acousticness = mean(acousticness, na.rm = TRUE),
      avg_loudness = mean(loudness, na.rm = TRUE)
    ) %>%
    arrange(snapshot_date)

  return(daily_baseline)
}

#' 2. Find the "Peak Event Days" from the News Data
#' Since a search like "earthquake" might have residual news for weeks,
#' we need to pinpoint the EXACT day the event broke.
#' @param news_df The appended all_news_3y dataframe
#' @param keyword The event keyword to look for
find_peak_event_days <- function(news_df = guardian, keyword = "Brazil", min_articles = 5) {
  total_articles = 8
  # Filter news for the keyword and find days with abnormal spikes in coverage
  peak_days <- news_df %>%
    filter(str_detect(tolower(titulo), tolower(keyword)) |
             str_detect(tolower(tema), tolower(keyword))) %>%
    # Only keep days with significant coverage
    filter(total_articles >= min_articles) %>%
    # STEP 1: Sort globally from highest articles to lowest
    arrange(desc(total_articles)) %>%
    # STEP 2: Create the month grouping
    mutate(month_year = floor_date(data, "month")) %>%
    group_by(month_year) %>%
    # STEP 3: Grab the 1st row of each group (which is guaranteed to be the max due to the sort above)
    slice(1) %>%
    ungroup() %>%
    select(data, total_articles, titulo)

  return(peak_days)
}

#' 3. Calculate the Impact of a Single Event
#' Compares 7 days before vs 7 days after the event.
#' @param event_date The Date of the shock
#' @param daily_spotify The aggregated Spotify baseline
#' @param window Number of days to look before and after
analyze_event_window <- function(event_date, daily_spotify, window = 7) {

  # Define the Pre and Post windows
  pre_start <- event_date - days(window)
  pre_end <- event_date - days(1)

  post_start <- event_date + days(1)
  post_end <- event_date + days(window)

  # Filter and label the Spotify data
  window_data <- daily_spotify %>%
    filter(snapshot_date >= pre_start & snapshot_date <= post_end) %>%
    filter(snapshot_date != event_date) %>% # Exclude the actual day to avoid partial-day noise
    mutate(
      period = case_when(
        snapshot_date <= pre_end ~ "Pre-Event",
        snapshot_date >= post_start ~ "Post-Event"
      ),
      period = factor(period, levels = c("Pre-Event", "Post-Event"))
    )

  # If we don't have enough data (e.g., event is at the very edge of dataset), skip
  if(nrow(window_data) < (window * 2)) return(NULL)

  # Calculate % change and run T-Tests for each audio feature
  features <- c("avg_valence", "avg_energy", "avg_danceability", "avg_acousticness")
  results <- list()

  for(feat in features) {
    # Calculate means
    pre_mean <- mean(window_data[[feat]][window_data$period == "Pre-Event"], na.rm = TRUE)
    post_mean <- mean(window_data[[feat]][window_data$period == "Post-Event"], na.rm = TRUE)
    pct_change <- ((post_mean - pre_mean) / pre_mean) * 100

    # Run statistical T-test to see if the shift is real or just random noise
    t_test <- t.test(window_data[[feat]] ~ window_data$period)
    p_value <- t_test$p.value

    results[[feat]] <- tibble(
      feature = feat,
      pre_mean = pre_mean,
      post_mean = post_mean,
      pct_change = pct_change,
      p_value = p_value,
      is_significant = p_value < 0.05
    )
  }

  final_result <- bind_rows(results) %>% mutate(event_date = event_date)
  return(final_result)
}

terms_to_analyze <- c("earthquake",
                      "attack",
                      "war",
                      "Lula",
                      "Bolsonaro",
                      "election",
                      "oscar",
                      "louvre",
                      "COP",
                      "olympics",
                      "Madonna",
                      "amy winehouse",
                      "bob marley",
                      "Diddy",
                      "6ix9ine",
                      "tornado",
                      "hurricane",
                      "tsunami",
                      "cyclone",
                      "storm","snowstorm")
my_search_terms <- terms_to_analyze
#' 4. The Master Execution Pipeline
#' Loops through your list of search terms and builds the final impact report.
#' @param spotify_raw The 2.1M row dataframe
#' @param news_raw The appended 3-year news dataframe
#' @param terms_to_analyze Vector of keywords
run_global_event_study <- function(spotify_raw = spotify_processed, news_raw = guardian, terms_to_analyze) {

  # 1. Prep the Spotify data
  daily_spotify <- aggregate_daily_spotify(spotify_raw)

  all_impact_results <- list()

  # 2. Loop through every requested event type
  for(term in terms_to_analyze) {
    cat(sprintf("\nAnalyzing events related to: '%s'...\n", term))

    # Find the peak days this event happened in the news
    peak_events <- find_peak_event_days(news_raw, term, min_articles = 5)

    if(nrow(peak_events) == 0) {
      cat("  -> No major spikes found for this term. Skipping.\n")
      next
    }

    # 3. Analyze the music shifts around each of those peak days
    for(i in 1:nrow(peak_events)) {
      event_date <- peak_events$data[i]
      headline <- peak_events$titulo[i]

      impact <- analyze_event_window(event_date, daily_spotify, window = 7)

      if(!is.null(impact)) {
        impact <- impact %>%
          mutate(
            event_type = term,
            headline = headline
          )
        all_impact_results[[paste(term, event_date, sep="-")]] <- impact
      }
    }
  }

  # Combine everything into one beautiful master table
  final_report <- bind_rows(all_impact_results) %>%
    # Reorder columns for easier reading
    select(event_type, event_date, headline, feature, pre_mean, post_mean, pct_change, p_value, is_significant)

  return(final_report)
}

# =====================================================================
# EXECUTE THE PIPELINE
# =====================================================================
library(tidyverse)
library(stringr)

#' Extract Top Real-World Events Automatically from Guardian Tags
#'
#' @param news_df The appended all_news_3y dataframe
#' @param top_n How many distinct topics/events to analyze
#' @return A character vector of the top specific topics
extract_dynamic_topics <- function(news_df = guardian, top_n = 100) {
  cat("Scanning 3 years of news to identify the biggest global topics...\n")

  # List of generic Guardian sections to ignore so we get specific events
  # You can add to this list if generic terms slip through
  generic_stopwords <- c(
    "world news", "life and style", "newspapers & magazines", "society",
    "culture", "media", "news", "politics", "global development",
    "americas", "europe", "uk news", "us news", "australia news",
    "environment", "business", "science", "technology", "film", "music"
  )

  top_topics <- news_df %>%
    # 1. Split the massive strings of themes into individual rows
    # Your aggregated data uses "|" for new articles and ";" for tags within articles
    separate_rows(tema, sep = "[;|]") %>%

    # 2. Clean up the text
    mutate(topic = str_squish(tolower(tema))) %>%

    # 3. Filter out empty strings and generic news categories
    filter(str_length(topic) > 2) %>%
    filter(!topic %in% generic_stopwords) %>%

    # 4. Count the frequency of each specific tag
    count(topic, name = "total_mentions") %>%
    arrange(desc(total_mentions)) %>%

    # 5. Take the top N most talked-about specific topics
    head(top_n) %>%
    pull(topic)

  cat(sprintf("Found top %d topics to analyze!\n", top_n))
  print(top_topics)

  return(top_topics)
}


# =====================================================================
# EXECUTE THE FULLY AUTOMATED PIPELINE
# =====================================================================

# 1. Automatically extract the top 20 biggest specific themes/events from the news
dynamic_search_terms <- extract_dynamic_topics(guardian, top_n = 100)

# 2. Run the Event Study using those automatically generated terms
final_event_impact_report <- run_global_event_study(
  spotify_raw = spotify_processed,
  news_raw = guardian,
  terms_to_analyze = terms_to_analyze
)

# 3. View the statistically significant behavioral shifts!
significant_shifts <- final_event_impact_report %>% filter(is_significant == TRUE)
View(significant_shifts)

# RUN THE ANALYSIS
final_event_impact_report <- run_global_event_study(spotify_processed, guardian, my_search_terms)

# View the shifts that were actually statistically significant!
significant_shifts <- final_event_impact_report %>% filter(is_significant == TRUE)
View(significant_shifts)


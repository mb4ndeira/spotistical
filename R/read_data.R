#' Read Data
#'
#' @param minis
#' @param data
#'
#' @returns env with processed data
#' @export csv and parquet files to env
#'
#' @examples
library(dplyr)
library(arrow)
library(Matrix)
spotify_processed <- arrow::read_parquet("./data/spotify_processed.parquet")

readData <- function(minis = FALSE, data = file.path("../data/")) {
  spotify_processed = arrow::read_parquet("./data/spotify_processed.parquet")
  return(spotify_processed)

  if (minis == TRUE) {
    return(miniBR30) = read.csv(file = "./data/minis30.csv")
    return(minis30) = read.csv(file = "./data/minis30.csv")
  }
}

readData()

save_env_to_parquet <- function(output_dir = "env_parquet") {
  # 1. Ensure the arrow package is loaded
  if (!requireNamespace("arrow", quietly = TRUE)) {
    stop("The 'arrow' package is required. Install it using install.packages('arrow').")
  }

  # 2. Get all objects in the global environment
  all_objects <- ls(envir = .GlobalEnv)

  # 3. Filter for data frames and tibbles
  df_names <- Filter(function(x) inherits(get(x, envir = .GlobalEnv), "data.frame"), all_objects)

  # 4. Check if any data frames exist
  if (length(df_names) == 0) {
    message("No data frames found in the global environment.")
    return(invisible(NULL))
  }

  # 5. Create the output directory
  dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

  # 6. Loop and save each data frame
  for (df_name in df_names) {
    df_obj <- get(df_name, envir = .GlobalEnv)
    file_path <- file.path(output_dir, paste0(df_name, ".parquet"))

    arrow::write_parquet(df_obj, file_path)
    message(paste("Successfully saved:", file_path))
  }
}

# =====================================================================
# GDELT API 2.0 INTEGRATION MODULE
# =====================================================================

# Install if necessary: install.packages(c("httr", "jsonlite", "tidyverse", "lubridate"))
library(httr)
library(jsonlite)
library(tidyverse)
library(lubridate)

#' Fetch Daily News Volume and Sentiment (Tone) from GDELT
#'
#' GDELT's 'TimelineTone' mode returns a daily time-series showing the
#' average sentiment of all articles matching your query.
#'
#' @param query The search term (e.g., '"economic crash"', '"Taylor Swift"', or 'climate')
#' @param timespan How far back to look (e.g., "1m" for 1 month, "1y" for 1 year)
#' @return A clean dataframe with Date, Volume, and Average Tone
fetch_gdelt_timeline_tone <- function(query, timespan = "3m") {
  cat(paste("Querying GDELT API for:", query, "over the last", timespan, "...\n"))

  # GDELT 2.0 DOC API Endpoint
  base_url <- "https://api.gdeltproject.org/api/v2/doc/doc"

  # Construct the API request parameters
  # mode = TimelineTone (gives us the time series of sentiment)
  res <- GET(
    url = base_url,
    query = list(
      query = query,
      mode = "TimelineTone",
      format = "json",
      timespan = timespan
    )
  )

  # Error handling: Check if the API request was successful
  if (http_status(res)$category != "Success") {
    stop("Failed to fetch data from GDELT. HTTP Status: ", status_code(res))
  }

  # Parse the JSON response
  json_text <- content(res, as = "text", encoding = "UTF-8")
  parsed_data <- fromJSON(json_text)

  # Check if GDELT found any results
  if (length(parsed_data$timeline) == 0) {
    warning("No news articles found for this query in the given timespan.")
    return(NULL)
  }

  # Extract the time series data
  # GDELT returns 'data' which contains the date, volume, and average tone
  timeline_df <- as_tibble(parsed_data$timeline[[1]]$data)

  # Clean up the dataset
  clean_df <- timeline_df %>%
    mutate(
      # GDELT dates look like "20231024T000000Z", parse them to standard Dates
      snapshot_date = as.Date(ymd_hms(date)),
      # GDELT Tone ranges roughly from -10 (very negative) to +10 (very positive)
      global_sentiment_score = value
    ) %>%
    # If looking at months, group by day to match your Spotify snapshot_dates
    group_by(snapshot_date) %>%
    summarise(
      global_sentiment_score = mean(global_sentiment_score, na.rm = TRUE),
      daily_news_volume = n() # Note: TimelineTone aggregates, so this is just a frequency count of data points
    ) %>%
    arrange(snapshot_date)

  return(clean_df)
}

#' Fetch Top Actual Headlines from GDELT (For Context)
#'
#' Useful for seeing exactly WHAT happened on a specific day
#' when you spot an anomaly in your Spotify charts.
#'
#' @param query The search term
#' @param max_records Number of articles to return (max 250)
#' @return A dataframe of articles with URLs and Titles
fetch_gdelt_articles <- function(query, max_records = 50) {
  base_url <- "https://api.gdeltproject.org/api/v2/doc/doc"

  res <- GET(
    url = base_url,
    query = list(
      query = "Ozempic",
      mode = "ArtList",
      format = "json",
      maxrecords = 50,
      sort = "ToneDesc" # Sort by most positive to most negative, or use "DateDesc"
    )
  )

  if (http_status(res)$category != "Success") stop("API Error")

  parsed_data <- fromJSON(content(res, as = "text", encoding = "UTF-8"))

  if(length(parsed_data$articles) == 0) return(NULL)

  articles_df <- as_tibble(parsed_data$articles) %>%
    select(url, title, domain, tone, seendate) %>%
    mutate(seendate = ymd_hms(seendate))

  return(articles_df)
}

# =====================================================================
# TEST THE CONNECTION
# =====================================================================

# Example 1: Get the global sentiment timeline for "economy" over the last 3 months
# economy_tone <- fetch_gdelt_timeline_tone('"economy"', timespan = "3m")
# print(head(economy_tone))

# Example 2: Get specific headlines about Spotify to see what's happening
# spotify_news <- fetch_gdelt_articles('"spotify"', max_records = 10)
# print(spotify_news$title)

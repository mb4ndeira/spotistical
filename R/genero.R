# Install the official Spotify API wrapper for R
# install.packages("spotifyr")
library(spotifyr)
library(tidyverse)

# ==========================================
# 1. AUTHENTICATE WITH SPOTIFY
# ==========================================
# You get these from developer.spotify.com/dashboard
Sys.getenv("SPOTIFY_CLIENT_ID")
Sys.getenv("SPOTIFY_CLIENT_SECRET")
access_token <- get_spotify_access_token()

# ==========================================
# 2. USE YOUR EXISTING 516-ITEM LIST
# ==========================================
cat("Using your existing 'artist_genres' list...\n")

# Clean your existing list just in case there are duplicates
# New Code: Convert the list to a dataframe first!
local_genres <- tibble(
  primary_artist = names(artist_genres),
  genre = unlist(artist_genres)
) %>%
  distinct(primary_artist, .keep_all = TRUE)

# Get the list of all unique artists in your massive 2.1M dataset
target_artists <- spotify_processed %>%
  mutate(primary_artist = str_split(artists, ",", simplify = TRUE)[,1]) %>%
  distinct(primary_artist) %>%
  filter(primary_artist != "" & !is.na(primary_artist))

# Subtract the 516 we already have in memory!
artists_to_fetch <- target_artists %>%
  anti_join(local_genres, by = "primary_artist")

cat("Artists skipped because they are in your 516 list:", nrow(target_artists) - nrow(artists_to_fetch), "\n")

# ==========================================
# 3. CHECK PREVIOUS DISK PROGRESS
# ==========================================
progress_file <- "artist_genres_progress.csv"

if (file.exists(progress_file)) {
  progress_db <- read.csv(progress_file)
  # Remove artists we've already fetched in a previous run and saved to disk
  artists_to_fetch <- artists_to_fetch %>%
    anti_join(progress_db, by = "primary_artist")
  cat("Found progress file on disk! Resuming...\n")
} else {
  # Create an empty progress file if it doesn't exist
  write.table(data.frame(primary_artist=character(), genre=character()),
              file = progress_file, sep=",", row.names=FALSE, col.names=TRUE)
}

cat("Total artists remaining to fetch from API:", nrow(artists_to_fetch), "\n\n")

# ==========================================
# 4. THE SMART API BATCH LOOP
# ==========================================
if (nrow(artists_to_fetch) > 0) {

  batch_size <- 50
  current_batch_df <- data.frame(primary_artist=character(), genre=character())

  for (i in 1:nrow(artists_to_fetch)) {
    artist_name <- artists_to_fetch$primary_artist[i]
    fetched_genre <- NA

    tryCatch({
      search_result <- search_spotify(artist_name, type = "artist", limit = 1)

      if (nrow(search_result) > 0 && length(unlist(search_result$genres[1])) > 0) {
        fetched_genre <- paste(unlist(search_result$genres[1]), collapse = ", ")
      } else {
        fetched_genre <- "unknown"
      }

    }, error = function(e) {
      if (grepl("429", e$message)) {
        cat("\n[!] Rate Limit (429) hit! Pausing for 45 seconds to let Spotify cool down...\n")
        Sys.sleep(45)
      } else {
        cat("\n[!] Minor error on:", artist_name, "- Skipping...\n")
      }
    })

    if (!is.na(fetched_genre)) {
      current_batch_df <- rbind(current_batch_df, data.frame(primary_artist = artist_name, genre = fetched_genre))
    }

    # Pause 0.15s between calls to prevent the 429 error
    Sys.sleep(0.15)

    # Save to disk every 50 artists
    if (i %% batch_size == 0 || i == nrow(artists_to_fetch)) {
      write.table(current_batch_df, file = progress_file, sep=",", row.names=FALSE, col.names=FALSE, append=TRUE)
      cat(paste0("Processed & Saved: ", i, " / ", nrow(artists_to_fetch), " artists...\n"))
      current_batch_df <- data.frame(primary_artist=character(), genre=character())
    }
  }
  cat("\nAPI Fetching Complete!\n")
}

# ==========================================
# 5. MERGE EVERYTHING TOGETHER
# ==========================================
# Load the API progress from disk
final_api_data <- read.csv(progress_file)

# Master dictionary = Your 516 in-memory list + Everything the API just saved to disk
master_genre_dictionary <- bind_rows(local_genres, final_api_data) %>%
  distinct(primary_artist, .keep_all = TRUE)

# Join it back to your 2.1 million row dataset
spotify_final <- spotify_processed %>%
  mutate(primary_artist = str_split(artists, ",", simplify = TRUE)[,1]) %>%
  left_join(master_genre_dictionary, by = "primary_artist") %>%
  select(-primary_artist) # Clean up

cat("\nDone! All available genres successfully appended to your dataset.\n")
# ==========================================
# 2. BUILD A LOCAL DICTIONARY TO SAVE API CALLS
# ==========================================
cat("Scanning local dataset.csv to minimize API calls...\n")

# Load your original dataset
original_db <- read.csv("dataset.csv")

# Extract known artists and genres
local_genres <- original_db %>%
  # Handle potential multiple artists in the original dataset
  mutate(primary_artist = str_split(artists, ";|\\,", simplify = TRUE)[,1]) %>%
  select(primary_artist, track_genre) %>%
  rename(genre = track_genre) %>%
  distinct(primary_artist, .keep_all = TRUE)

# Get the list of all unique artists in your massive 2.1M dataset
target_artists <- spotify_processed %>%
  mutate(primary_artist = str_split(artists, ",", simplify = TRUE)[,1]) %>%
  distinct(primary_artist) %>%
  filter(primary_artist != "" & !is.na(primary_artist))

# Filter out the artists we already found in dataset.csv!
artists_to_fetch <- target_artists %>%
  anti_join(local_genres, by = "primary_artist")

cat("Artists covered by local data:", nrow(target_artists) - nrow(artists_to_fetch), "\n")

# ==========================================
# 3. CHECK PREVIOUS PROGRESS
# ==========================================
progress_file <- "artist_genres_progress.csv"

if (file.exists(progress_file)) {
  progress_db <- read.csv(progress_file)
  # Remove artists we've already fetched in a previous run
  artists_to_fetch <- artists_to_fetch %>%
    anti_join(progress_db, by = "primary_artist")
  cat("Found progress file! Resuming...\n")
} else {
  # Create an empty progress file with headers if it doesn't exist
  write.table(data.frame(primary_artist=character(), genre=character()),
              file = progress_file, sep=",", row.names=FALSE, col.names=TRUE)
}

cat("Total artists remaining to fetch from API:", nrow(artists_to_fetch), "\n\n")

# ==========================================
# 4. THE SMART API BATCH LOOP
# ==========================================
# If we have 0 left, skip the loop!
if (nrow(artists_to_fetch) > 0) {

  # Variables for batching
  batch_size <- 50
  current_batch_df <- data.frame(primary_artist=character(), genre=character())

  for (i in 1:nrow(artists_to_fetch)) {
    artist_name <- artists_to_fetch$primary_artist[i]
    fetched_genre <- NA

    # Try/Catch block with Rate Limit handling
    tryCatch({
      search_result <- search_spotify(artist_name, type = "artist", limit = 1)

      if (nrow(search_result) > 0 && length(unlist(search_result$genres[1])) > 0) {
        fetched_genre <- paste(unlist(search_result$genres[1]), collapse = ", ")
      } else {
        fetched_genre <- "unknown" # Mark as unknown so we don't keep searching for them
      }

    }, error = function(e) {
      # If the error is a 429, we need to back off
      if (grepl("429", e$message)) {
        cat("\n[!] Rate Limit (429) hit! Pausing for 45 seconds to let Spotify cool down...\n")
        Sys.sleep(45)
      } else {
        cat("\n[!] Minor error on:", artist_name, "- Skipping...\n")
      }
    })

    # If we successfully got a result (even "unknown"), add to our batch dataframe
    if (!is.na(fetched_genre)) {
      current_batch_df <- rbind(current_batch_df, data.frame(primary_artist = artist_name, genre = fetched_genre))
    }

    # STANDARD PAUSE: 0.15 seconds between every call to avoid triggering the 429 in the first place
    Sys.sleep(0.15)

    # BATCH SAVE: Every 50 artists, append to the CSV and clear the memory
    if (i %% batch_size == 0 || i == nrow(artists_to_fetch)) {
      # Append to CSV
      write.table(current_batch_df, file = progress_file, sep=",", row.names=FALSE, col.names=FALSE, append=TRUE)
      cat(paste0("Processed & Saved: ", i, " / ", nrow(artists_to_fetch), " artists...\n"))

      # Clear the batch dataframe for the next 50
      current_batch_df <- data.frame(primary_artist=character(), genre=character())
    }
  }
  cat("\nAPI Fetching Complete!\n")
}

# ==========================================
# 5. MERGE EVERYTHING TOGETHER
# ==========================================
# Load the full API progress
final_api_data <- read.csv(progress_file)

# Combine the local dataset genres with our newly fetched API genres
master_genre_dictionary <- bind_rows(local_genres, final_api_data) %>%
  distinct(primary_artist, .keep_all = TRUE)

# Join it back to your 2.1 million row dataset!
spotify_final <- spotify_processed %>%
  mutate(primary_artist = str_split(artists, ",", simplify = TRUE)[,1]) %>%
  left_join(master_genre_dictionary, by = "primary_artist") %>%
  select(-primary_artist) # Clean up

cat("\nDone! All available genres successfully appended to your dataset.\n")
# ==========================================
# 2. CREATE A UNIQUE ARTIST LOOKUP TABLE
# ==========================================
# Extract the 13,727 unique artists from your dataset
unique_artists <- spotify_processed %>%
  select(artists) %>%
  distinct() %>%
  # Handle cases where multiple artists are separated by commas (e.g., "Lady Gaga, Ariana Grande")
  # We just take the primary artist for genre classification
  mutate(primary_artist = str_split(artists, ",", simplify = TRUE)[,1])

# ==========================================
# 3. FETCH GENRES FROM API (WITH RATE LIMIT HANDLING)
# ==========================================
# Create an empty list to store results
artist_genres <- list()

cat("Fetching genres for", nrow(unique_artists), "artists...\n")

# Loop through unique artists (This will take a little while to run!)
for (i in 1:nrow(unique_artists)) {
  artist_name <- unique_artists$primary_artist[i]

  # Skip empty names
  if(artist_name == "" | is.na(artist_name)) next

  # Try/Catch block to prevent the loop from crashing if the API glitches
  tryCatch({
    # Search Spotify for the artist
    search_result <- search_spotify(artist_name, type = "artist", limit = 1)

    # If an artist is found, extract their genres
    if (nrow(search_result) > 0) {
      # Spotify returns genres as a list, we collapse them into a single string: "pop, dance pop"
      genres <- paste(unlist(search_result$genres[1]), collapse = ", ")

      # Add to our list
      artist_genres[[artist_name]] <- genres
    }
  }, error = function(e) {
    cat("Error fetching:", artist_name, "\n")
  })

  # CRITICAL: Pause for 0.1 seconds so Spotify doesn't ban your IP for spamming
  Sys.sleep(0.1)

  # Print progress every 100 artists
  if(i %% 100 == 0) cat(i, "artists processed...\n")
}

 # ==========================================
# 4. MERGE BACK TO MAIN DATASET
# ==========================================
# Convert our fetched list into a dataframe
genre_df <- tibble(
  primary_artist = names(artist_genres),
  genre = unlist(artist_genres)
)

# Join it back to your 2.1 million row dataset!
spotify_final <- spotify_processed %>%
  mutate(primary_artist = str_split(artists, ",", simplify = TRUE)[,1]) %>%
  left_join(genre_df, by = "primary_artist") %>%
  select(-primary_artist) # Clean up the temp column

cat("Done! Genres successfully appended.")

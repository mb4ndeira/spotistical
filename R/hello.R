# Hello, world!
#
# This is an example function named 'hello'
# which prints 'Hello, world!'.
#
# You can learn more about package authoring with RStudio at:
#  
#   https://r-pkgs.org
#
# Some useful keyboard shortcuts for package authoring:
#
#   Install Package:           'Cmd + Shift + B'
#   Check Package:             'Cmd + Shift + E'
#   Test Package:              'Cmd + Shift + T'

# 1. Extract the year from the snapshot_date column
# (Wrapping in as.Date ensures it works even if it's currently a character string)
years <- format(as.Date(spotify$snapshot_date), "%Y")

# 2. Split the original dataframe into a list of dataframes based on the year
spotify_list <- split(spotify, years)

# 3. Rename the list elements to match your desired format (spotify_YEAR)
names(spotify_list) <- paste0("spotify_", names(spotify_list))

# 4. Export the list items into your global environment as individual dataframes
list2env(spotify_list, envir = .GlobalEnv)

# (Optional) Remove the original massive dataset and list to free up RAM
# rm(spotify, spotify_list)


# Install if you don't have it: install.packages("data.table")
library(data.table)

# Loop through the names of the list ("spotify_2023", "spotify_2024", etc.)
lapply(names(spotify_list), function(dataset_name) {

  # Construct the file name (e.g., "spotify_2023.csv")
  file_name <- paste0(dataset_name, ".csv")

  # Write the specific dataframe to your working directory
  fwrite(spotify_list[[dataset_name]], file = file_name)

})

# 1. Find the exact middle row
n_rows <- nrow(spotify_2024)
midpoint <- floor(n_rows / 2)

# 2. Slice the dataframe into two halves using row indices
spotify_2024_part1 <- spotify_2024[1:midpoint, ]
spotify_2024_part2 <- spotify_2024[(midpoint + 1):n_rows, ]

# 3. Write them out (using data.table's fwrite for speed)
library(data.table)
fwrite(spotify_2024_part1, file = "spotify_2024_part1.csv")
fwrite(spotify_2024_part2, file = "spotify_2024_part2.csv")

# (Optional) Clean up your environment if you are short on RAM
# rm(spotify_2024, spotify_2024_part1, spotify_2024_part2)

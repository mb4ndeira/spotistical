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

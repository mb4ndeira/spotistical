#########################
if (!require("tidyverse")) install.packages("tidyverse")
if (!require("readr")) install.packages("readr")
if (!require("dplyr")) install.packages("dplyr")
if (!require("tidytext")) install.packages("tidytext")
library(tidyverse)
library(readr)
library(dplyr)
library(tidytext)
library(stringr) # Part of the tidyverse package

#########################
query <- "'Joe Biden'" #Enter search term(s)
startdate <- "20230102" #Enter preferred start date
enddate <- "20230219" #Enter preferred end date
sources <- c("washingtonpost.com",
             "nytimes.com") #Enter sources to search

#########################
#Generating a sequence of dates
startdate2 <- as.Date(startdate,"%Y%m%d")
enddate2 <- as.Date(enddate,"%Y%m%d")
dates <- seq(as.Date(startdate2), as.Date(enddate2), "days")
dates <- format(dates, "%Y%m%d")
#Estimating run time for query
Minutes <- round((length(sources)*(length(dates)*2.5/60)), digits = 1)
Hours <- round((length(sources)*(length(dates)*2.5/3600)), digits = 1)
print(paste0("In minutes: ",Minutes,". In hours: ",Hours,"."))

#########################
#Creating the dataframe
Headlines = data.frame(
  Source = character(),
  URL = character(),
  MobileURL = character(),
  Date = character(),
  Title = character(),
  stringsAsFactors = FALSE)

#Defining the query URL parts
URL_p1 <- "https://api.gdeltproject.org/api/v2/doc/doc?query="
URL_p2 <- " domainis:"
#URL_p2 <- " repeat3:\"Biden\" domainis:"
URL_p3 <- "&mode=artlist&maxrecords=250&sort=datedesc&startdatetime="
URL_p4 <- "000000&enddatetime="
URL_p5 <- "235959&format=CSV"

# For loops
for (thissource in sources)
{
  for (thisdate in dates)
  {
    URL_raw <- paste0(URL_p1,
                      query,
                      URL_p2,
                      thissource,
                      URL_p3,
                      thisdate,
                      URL_p4,
                      thisdate,
                      URL_p5)
    URL_encoded <- URLencode(URL_raw)
    print("---------------------------------")
    print("Getting data for")
    print(paste0(thisdate," ",thissource))
    print("---------------------------------")
    Thisfetch <- read_csv(URL_encoded, show_col_types = FALSE)
    Thisfetch$Source <- thissource
    print(paste0(nrow(Thisfetch)," rows"))
    Headlines <- rbind(Headlines,Thisfetch)
    Sys.sleep(2)
  }
}
#Deduplicate, check, and export data
Headlines <- Headlines[!duplicated(Headlines$URL),]
CountsBySource <- Headlines %>%
  group_by(Source) %>%
  summarize(HeadlineCount = n())
View(CountsBySource)
filename <- paste0(query,startdate,"to",enddate,".csv")
write_excel_csv(Headlines,filename)
#Cleanup
rm(Thisfetch,
   dates,
   enddate,
   enddate2,
   filename,
   query,
   sources,
   startdate,
   startdate2,
   thisdate,
   thissource,
   URL_encoded,
   URL_p1,
   URL_p2,
   URL_p3,
   URL_p4,
   URL_p5,
   URL_raw)
#View raw data frame
View(Headlines)

#########################
#Headline word counts
WordCounts <- Headlines %>%
  unnest_tokens(word,Title) %>%
  count(word, sort = TRUE)
# Deleting standard stop words
data("stop_words")
WordCounts <- WordCounts %>%
  anti_join(stop_words)
# Deleting custom stop words
my_stopwords <- tibble(word = c("and",
                                "the",
                                "etc."))
WordCounts <- WordCounts %>%
  anti_join(my_stopwords)
rm(stop_words,
   my_stopwords)
#Viewing word counts
View(WordCounts)

#########################
#Headline coding
searchterms <- "trump|maga"
Headlines$Trump <- ifelse(grepl(searchterms,
                                Headlines$Title,
                                ignore.case = TRUE),1,0)
searchterms <- "house|gop|republican|mccarthy"
Headlines$Republicans <- ifelse(grepl(searchterms,
                                      Headlines$Title,
                                      ignore.case = TRUE),1,0)
searchterms <- "classified documents"
Headlines$Documents <- ifelse(grepl(searchterms,
                                    Headlines$Title,
                                    ignore.case = TRUE),1,0)
searchterms <- "debt|ceiling"
Headlines$Debt <- ifelse(grepl(searchterms,
                               Headlines$Title,
                               ignore.case = TRUE),1,0)
searchterms <- "Jan. 6|capitol riot"
Headlines$Jan6 <- ifelse(grepl(searchterms,
                               Headlines$Title,
                               ignore.case = TRUE),1,0)
searchterms <- "China|Chinese"
Headlines$China <- ifelse(grepl(searchterms,
                                Headlines$Title,
                                ignore.case = TRUE),1,0)
searchterms <- "Ukraine|Ukranian|Russia"
Headlines$Ukraine <- ifelse(grepl(searchterms,
                                  Headlines$Title,
                                  ignore.case = TRUE),1,0)
searchterms <- "border|migra"
Headlines$Immigration <- ifelse(grepl(searchterms,
                                      Headlines$Title,
                                      ignore.case = TRUE),1,0)

#########################
# Categorizing by day and also by week
if (!require("lubridate")) install.packages("lubridate")
library(lubridate)
Headlines$Day <- round_date(Headlines$Date,
                            unit = "day")
Headlines$WeekOf <- round_date(Headlines$Date,
                               unit = "week",
                               week_start = getOption("lubridate.week.start",1))
#Aggregating by week
AggByWeek <- Headlines %>%
  group_by(WeekOf) %>%
  summarize(Trump = sum(Trump, na.rm=TRUE),
            Republicans = sum(Republicans, na.rm=TRUE),
            Documents = sum(Documents, na.rm=TRUE),
            Debt = sum(Debt, na.rm=TRUE),
            Jan6 = sum(Jan6, na.rm=TRUE),
            China = sum(China, na.rm=TRUE),
            Ukraine = sum(Ukraine, na.rm=TRUE),
            Immigration = sum(Immigration, na.rm=TRUE),
            ArticleCount = n())
#Aggregating by day
AggByDay <- Headlines %>%
  group_by(Day) %>%
  summarize(Trump = sum(Trump, na.rm=TRUE),
            Republicans = sum(Republicans, na.rm=TRUE),
            Documents = sum(Documents, na.rm=TRUE),
            Debt = sum(Debt, na.rm=TRUE),
            Jan6 = sum(Jan6, na.rm=TRUE),
            China = sum(China, na.rm=TRUE),
            Ukraine = sum(Ukraine, na.rm=TRUE),
            Immigration = sum(Immigration, na.rm=TRUE),
            ArticleCount = n())

#########################
#Graphing by week and by day
if (!require("plotly")) install.packages("plotly")
library(plotly)
# Color palettes: https://coolors.co/palettes/trending
# Graphing by week
fig <- plot_ly(AggByWeek, x = ~WeekOf, y = ~Trump,
               name = 'Trump', type = 'scatter',
               mode = 'none', stackgroup = 'one',
               fillcolor = '#F94144')
fig <- fig %>% add_trace(y = ~Republicans,
                         name = 'Republicans',
                         fillcolor = '#F3722C')
fig <- fig %>% add_trace(y = ~Documents, name = 'Documents',
                         fillcolor = '#F8961E')
fig <- fig %>% add_trace(y = ~Debt, name = 'Debt',
                         fillcolor = '#F9844A')
fig <- fig %>% add_trace(y = ~Jan6, name = 'Jan. 6',
                         fillcolor = '#90BE6D')
fig <- fig %>% add_trace(y = ~China, name = 'China',
                         fillcolor = '#43AA8B')
fig <- fig %>% add_trace(y = ~Ukraine, name = 'Ukraine',
                         fillcolor = '#4D908E')
fig <- fig %>% add_trace(y = ~Immigration, name = 'Immigration',
                         fillcolor = '#577590')
fig <- fig %>% layout(title = 'Headline counts, by topic and week',
                      xaxis = list(title = "Week of",
                                   showgrid = FALSE),
                      yaxis = list(title = "Count",
                                   showgrid = TRUE))

fig

# Graphing by day
fig <- plot_ly(AggByDay, x = ~Day, y = ~Trump,
               name = 'Trump', type = 'scatter',
               mode = 'none', stackgroup = 'one',
               fillcolor = '#F94144')
fig <- fig %>% add_trace(y = ~Republicans,
                         name = 'Republicans',
                         fillcolor = '#F3722C')
fig <- fig %>% add_trace(y = ~Documents, name = 'Documents',
                         fillcolor = '#F8961E')
fig <- fig %>% add_trace(y = ~Debt, name = 'Debt',
                         fillcolor = '#F9844A')
fig <- fig %>% add_trace(y = ~Jan6, name = 'Jan. 6',
                         fillcolor = '#90BE6D')
fig <- fig %>% add_trace(y = ~China, name = 'China',
                         fillcolor = '#43AA8B')
fig <- fig %>% add_trace(y = ~Ukraine, name = 'Ukraine',
                         fillcolor = '#4D908E')
fig <- fig %>% add_trace(y = ~Immigration, name = 'Immigration',
                         fillcolor = '#577590')
fig <- fig %>% layout(title = 'Headline counts, by topic and week',
                      xaxis = list(title = "Week of",
                                   showgrid = FALSE),
                      yaxis = list(title = "Count",
                                   showgrid = TRUE))

fig

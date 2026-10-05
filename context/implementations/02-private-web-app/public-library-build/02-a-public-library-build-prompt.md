# Music Charts Archive

We are gonna use `musicchartsarchive.com` as the source of information

Read `context/app/01-app-context.md` and `context/implementations/02-private-web-app/02-prompt.md`. Your task is not to work on the plan, your task is to work on building a document `context/implementations/02-private-web-app/public-library-build/02-a-public-library-build-response.md` to get all the context another AI agent can take in order to start working on the building of this music library with real artists and real songs.

What I like about this site:
- Decades: if I select `https://musicchartsarchive.com/1970s` I can select the year
- Year: If I select the year from `Singles Charts from...` I get into `https://musicchartsarchive.com/singles-charts/1978` for example. Then I can see all the dates available for that year
- Date: when I click on a given valid date (i.e `https://musicchartsarchive.com/singles-chart/1978-02-11`) I get:

```text
1	Stayin' Alive	Bee Gees	
2	Short People	Randy Newman	
3	(Love Is) Thicker Than Water	Andy Gibb	
4	We Are The Champions	Queen	
5	Just The Way You Are	Billy Joel	
6	Sometimes When We Touch	Dan Hill	
7	Baby Come Back	Player
```

This is the ranking of that week for the singles charts.  

The objective first is to gather all this kind of information for all the decades, all the years, all the dates, so that we get all these rankings. We save them, and then from it we derive the unique list of artists and the unique list of song names.

From it, we will have to now deep dive. For every artist and for every song name, we will have to get the metadata out of it and the relationships of these entities. Think of it as a kind of graph in which we have as nodes of the graph the "song", "artist", "album" and some metadata inside of them.

Please propose metadata information for every entity of this graph so that it goes in line with my previous `context/app/01-app-context.md` document so that we don't keep any extra information that we don't need. 

So for example if I navigate onto a given song: `https://musicchartsarchive.com/singles/bee-gees/stayin-alive` I see there the album `https://musicchartsarchive.com/albums/soundtrack/saturday-night-fever`, I see the Chart History of that song:

```text
Chart Date	Position
1977-12-10	65
1977-12-17	52
1977-12-24	39
1977-12-31	39
1978-01-07	28
1978-01-14	17
```
(very useful to compute the popularity of that song)

When we are in the artist page we see `https://musicchartsarchive.com/artists/bee-gees` where we can get the albums and all the list of singles and their year (so yes some information for the metadata may be scattered).

Since some information is scattered, maybe I recommend you do a first, very high-level bulk download of all the information that you can parse and automatically retrieve from web scraping automated scripts. Be careful. I don't know if you will get banned because of a lot of requests, but we will learn it on the way if we get banned by web scraping automated scripts. Overall, the idea is to do a first get of all the information locally. We have enough space to save all this information because, at the end, it's just text files. At the end, what I want you to do is to then automate some scripts in order to organize this information into the final information model that will allow us to have all the information that we need, all the metadata we need, for every entity that we have.

There is one entity, or one kind of metadata, that we have for songs: the region, no? We say that it's worldwide, or maybe it's Spain or it's Catalan, the region. Here we are operating with worldwide, so everything that you will download here will have the region worldwide.

We also want to keep track of albums (some songs may not belong to an album so it is fine, make this optional) but if so we see also metadata that we want to store for that album (e.g `https://musicchartsarchive.com/albums/taylor-swift/folklore`)
```text
Track List: 
1. "The 1"
2. "Cardigan"
3. "The Last Great American Dynasty"
4. "Exile" (featuring Bon Iver)
5. "My Tears Ricochet"
6. "Mirrorball"
7. "Seven"
8. "August"
9. "This Is Me Trying"
10. "Illicit Affairs"
11. "Invisible String"
12. "Mad Woman"
13. "Epiphany"
14. "Betty"
15. "Peace"
16. "Hoax"
Physical bonus track. <- this kind of text that is not under a numbering format can be ignored
17. "The Lakes"
```

and albums also have chart history:
```text
Chart Date	Position
2020-08-08	1
2020-08-15	1
2020-08-22	1
2020-08-29	1
2020-09-05	1
2020-09-12	1
2020-09-19	5
2020-09-26	4
2020-10-03	1
2020-10-10	7
```

so that we can use the same popularity computation we will do for songs also for the albums to have computed the popularity of an album too. 

Of course a song can have multiple artists (e.g `https://musicchartsarchive.com/singles/pitbull/give-me-everything`) see how they are rendered so that we can extract them properly as the artist entity (do not parse artists by the song name or artists names, artists should be a link to their artist page, if an artist does not have an arists page, let's ignore it)

**Lyrics**: let's save the lyrics as metadata of the song

# Code

Write a new folder in `scripts/` about this Music Library generation process.
Create a `.music-library/` folder, and inside of it a `raw/` folder where you can save everything you download. Keep it organized and use some folder hierarchy similar to the one in the website we download the information so that we don't end up with folders having tones of files in it. Choose the right data format to save the data for all the entities and their relationships.
I want at the end all this data to live in a relational database so think of its design (don't create any graph database)
Try always to follow a systematic approach, for example for the dates, it is not worth repeating the dates because maybe you realize that they use the same dates for all the weeks, so we can normalize this data to avoid repeating all the date entries and maybe using ids and a table referencing the date is enough... so be tactial about it. 

# Metadata
You will see that in the implementation plan of our web app, there are other fields for the metadata to be filled, like the genre, or maybe some tags or some region. All the information that you don't find there, it's okay. Don't invent it. Don't try to be compliant and invent it. Simply don't include it. This task of this implementation plan is basically to download the data and see how to properly normalize it in a database, we don't want any integration yet with the rest of things in the app. 

# Already working process

There is an agent that is ongoing and working on the implementation in `context/implementations/02-private-web-app` Please, any script that you create should be put in the scripts folder, and all the data should be in the folder that I told you, so that we don't overlap with that AI agent at all.

# Implementation Plan
Write first a `context/implementations/02-private-web-app/public-library-build/02-a-public-library-build-plan.md`, following the guidelines in `context/language` (read both files). So don't produce anything yet, simply visualize everything, read all the context you need and you can investigate a bit the format of the files of this website to write the proper implementation plan and ask questions if you need my input (use clear language on questions, provide me the right context first, and then tell me always a recommended option first)
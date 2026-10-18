# Spain's weekly charts begin in 2002; Catalonia's in 2018

Spain has a full weekly chart, with every place, only from the week dated 30 December 2001. Catalonia has a measured chart only from summer 2018. Everything earlier is number ones, unsourced Top 10s, scans, awards, or lists made long after the fact. For `spain`, the PROMUSICAE song chart is online week by week: on spanishcharts.com from 2002, as PDFs on promusicae.es from 2004, and on El Portal de Música from August 2009. It was a Top 20 until 2008, a Top 50 from 2009, and a Top 100 that counts streaming from 2015. Los 40 Principales adds a weekly radio list, with all 40 places from January 2004 and the number one alone back to July 1966. Before 2002, the only free, machine-readable signal is the weekly number one (1959–2001), plus two partial sets of deeper places: Spanish Wikipedia's unsourced weekly Top 10s for 1982–1996, and Top 20 PDFs for 1960–1965. The whole 1970s, and 1997–2001, have nothing below number one as data. For `catalan`, the only ranked, measured source is the APECAT/BMAT monthly TOP 30: the 30 Catalan-language songs most played on 16 stations, published as 99 PDFs from September 2018 to September 2026. Before it there are one listener poll from 1986, yearly awards, Enderrock's YouTube top 100s from 2017, and a Viquipèdia table of cumulative Spotify plays. No chart source has an open licence. PROMUSICAE allows "strictly private" use and LOS40 "personal and private" viewing, which fits an app that stays on a home network and is never published. Wikipedia (CC BY-SA), Wikidata and the MusicBrainz core data (CC0) are the only openly licensed sources. The five sources to download first add up to about 2,800 requests, six to eight hours at a 5–10 second pace. The current formula needs two changes before that data arrives: a fixed reference chart size, so a week in a Top 20 is not scored like a week in the bottom half of a Top 100, and calibrated stand-ins for sources that give only number ones, monthly places, peaks or year-end ranks.

## PROMUSICAE's chart gives 25 years of weekly places, in three sizes

Spain had no industry chart until the late 1980s. From the 1960s to the 1980s, the "national" chart was a magazine or radio compilation. In turn these were Discomanía (Raúl Matas on Cadena SER), El Gran Musical's "Los Superventas", ABC's "Clasificación Nacional del Disco" and SER's own Superventas. The industry body was founded in 1958, became AFYVE in 1982 and **PROMUSICAE in 2004** ([Wikipedia EN](https://en.wikipedia.org/wiki/Productores_de_M%C3%BAsica_de_Espa%C3%B1a)). The sources disagree on when the AFYVE sales chart began. Spanish Wikipedia labels its lists AFYVE from 1982 ([1980s page](https://es.wikipedia.org/wiki/Anexo:Sencillos_n%C3%BAmero_uno_en_Espa%C3%B1a_en_la_d%C3%A9cada_de_1980)). The Discomanía blog switches its source to AFYVE only in 1988 ([Discomanía](https://revistadiscomania.wordpress.com/argentina-itunes-top-20/)).

The weekly PDFs themselves show how the chart changed:

- **Week 1 of 2004:** the chart was a **Top 20 of physical singles and maxi-singles**, compiled by Media Control ([PDF](https://www.promusicae.es/descarga-semanal/singles_1_26-diciembre-2003-a-01-enero-2004-n1952/)).
- **2008:** about 40 rows of download charts by Nielsen. They appear to be two Top 20s, one for downloads and one for ringtones ([PDF](https://www.promusicae.es/descarga-semanal/canciones_1_28-diciembre-2007-a-03-enero-2008-n474/)).
- **January 2009:** a **Top 50 Canciones** that combines physical and digital sales ([PDF](https://www.promusicae.es/descarga-semanal/canciones_1_26-diciembre-2008-a-01-enero-2009-n526/)).
- **First week of 2015:** a **Top 100 Canciones** that also counts Spotify, Deezer and other streaming services ([PDF](https://www.promusicae.es/descarga-semanal/canciones_1_26-diciembre-2014-a-01-enero-2015-n2777/)).

Three archives hold this chart, and they overlap. **promusicae.es** keeps one PDF per week per chart: physical singles from 2004 to 2008, "Canciones" from week 1 of 2008 to now, and a streaming chart for 2013–2014. That is about 1,300 PDFs (about 0.35 GB), and their text comes out cleanly with `pdftotext -layout`. Year-end lists run from 2004 to 2025 ([listas semanales](https://www.promusicae.es/listas-semanales/); [listas anuales](https://www.promusicae.es/listas-anuales/)). The site has no robots.txt but sits behind the Sucuri firewall. The file is chosen by the numeric ID at the end of the URL, not by the readable part of the name, so the links have to be collected from the archive's form, not built by hand.

**El Portal de Música**, PROMUSICAE's own HTML site, has weekly Top 100 Canciones pages from week 34 of 2009 to now, at `/lists/top-100-canciones/{YEAR}/{WEEK}`. They have 50 rows to 2014 and 100 from 2015, with peak, weeks on chart and certification. It also has year-end lists for 2009–2025, a Top 100 Streaming and a **Top 50 Radios airplay chart measured by BMAT** ([lists](https://www.elportaldemusica.es/lists); [Aviso Legal](https://www.elportaldemusica.es/site/aviso-legal)). The years the Top 50 Radios covers were not checked.

**spanishcharts.com**, run by Hung Medien (the family of sites around hitparade.ch), goes furthest back. Weeks back to **30/12/2001** load by URL even though its year menu starts at 2005. Its weekly pages show 20 songs to 2008, 50 from 2009 and 100 from 2015. It adds a physical Top 20 (2009–), a physical/digital Top 50 (2015–), number ones from 2005, and a page per song with its full weekly run ([weekly chart](https://spanishcharts.com/weekchart.asp?cat=s&year=2004&date=20041226); [song page](https://spanishcharts.com/showitem.asp?interpret=Aitana&titel=Superestrella&cat=s)). No year-end pages were found there.

The terms are the same in substance across all three. El Portal and promusicae.es both say that any use "que no sea estrictamente privada" (that is not strictly private) needs PROMUSICAE's written permission, and the PDFs carry "Prohibida la reproducción" (reproduction prohibited) ([promusicae.es Aviso Legal](https://www.promusicae.es/aviso-legal/)). spanishcharts.com has no terms page. Its robots.txt allows ordinary agents, blocks named AI crawlers, and declares `ai-train=no` as a reservation of rights under article 4 of EU Directive 2019/790 ([robots.txt](https://spanishcharts.com/robots.txt)). None of the three sets a Crawl-delay.

Spanish law gives the reason the terms matter. The sui generis database right in the LPI (arts. 133–136) lets the maker forbid extracting a substantial part of a database. The private-use exception covers only **non-electronic** databases, that is, books ([BOE, LPI](https://www.boe.es/buscar/act.php?id=BOE-A-1996-8930)). So for a home app the private-use permission in the sites' own terms is what carries the weight, not the law. This is a reading of the texts, not legal advice.

## Before 2002 the deep signal collapses to the number one

From 1959 to 2001 there is a complete run of weekly number ones and little else. English Wikipedia has a page for every year from 1959. The years 1959–1995 cite only Fernando Salaverri's book *Sólo éxitos: año a año, 1959–2002*, and 2003–2008 cite spanishcharts.com ([index](https://en.wikipedia.org/wiki/List_of_number-one_hits_(Spain)); [1965](https://en.wikipedia.org/wiki/List_of_number-one_singles_of_1965_(Spain))). The Discomanía blog's "Clasificación Nacional del Disco" is an independent cross-check. It lists one number one per period from 1960 to early 2016 and names the source for each entry:

- **Discomanía/SER**, fortnightly, 1960–62
- **El Gran Musical**, 1966–74
- **SER Superventas**, 1975–87
- **AFYVE**, 1988–2005

The same page links **404 one-page Top 20 PDFs**, dense for 1960–1965 (about 50 a year from 1962) and scattered after that ([Discomanía](https://revistadiscomania.wordpress.com/argentina-itunes-top-20/)).

The only free week-by-week places between 1966 and 2001 are on Spanish Wikipedia. Its pages "Sencillos más vendidos en España en YYYY" give **a weekly Top 10 for every year from 1982 to 1996**, labelled as AFYVE's. None of them cites a source, and 1987 has only 45 weeks ([1990](https://es.wikipedia.org/wiki/Anexo:Sencillos_m%C3%A1s_vendidos_en_Espa%C3%B1a_en_1990); [1987](https://es.wikipedia.org/wiki/Anexo:Sencillos_m%C3%A1s_vendidos_en_Espa%C3%B1a_en_1987)). The blog that Wikipedia used for the AFYVE lists of the 1990s, afyvecharts.blogspot.com, has been deleted ([checked live](https://afyvecharts.blogspot.com/)). It may survive in the Wayback Machine, but that was not checked. That leaves **1997–2001 with nothing below number one** in data form.

The deeper material that does exist needs a person or OCR to read it:

- **Salaverri's book.** About 1,046 pages and more than 10,000 titles, with each song's peak and weeks on chart, year by year. A second edition covers 1959–2012 ([Instituto Autor](https://institutoautor.org/biblioteca/solo-exitos-1959-2002-ano-a-ano/); [El Argonauta](https://www.elargonauta.com/libros/solo-exitos-1959-2012/978-84-8048-866-2/)). It is the one source where the law's private-extraction exception (LPI art. 135.1.a) clearly applies, because it is a printed database.
- **Billboard's "Hits of the World".** In the 1970s its Spain box was a Top 10 credited to a Spanish source: "El Musical" in a June 1972 issue, El Gran Musical in a January 1977 one ([1972 issue](https://www.worldradiohistory.com/Archive-All-Music/Billboard/70s/1972/BB-1972-06-17.pdf); [1977 page](https://www.worldradiohistory.com/hd2/IDX-Business/Music/Billboard-Index/IDX/1977/1977-01-08-Billboard-Page-0057.pdf)). On worldradiohistory.com, robots.txt disallows the single-page index scans under `/hd2/` but allows the full-issue PDFs under `/Archive-All-Music/`, which are about 13 MB each ([robots.txt](https://www.worldradiohistory.com/robots.txt)). Which years carried the Spain box, and who it was credited to in other years, was not checked.

## Los 40 adds a radio signal, complete only from 2004

Los 40 Principales is the only long-running radio list for Spain. The official site serves one server-rendered page per Saturday at `los40.com/lista40/listas-anteriores/YYYY-MM-DD`, from 16 July 1966 to the current week. **Every place (1–40) appears only from 3 January 2004.** Every page from 1966 to 27 December 2003 shows the number one alone ([2004-01-03](https://los40.com/lista40/listas-anteriores/2004-01-03); [2003-12-27](https://los40.com/lista40/listas-anteriores/2003-12-27)). A yearly page, `los40.com/lista40/numeros-1/YYYY`, gives all of that year's number ones for 1966–2026, so a full download needs only **61 year pages plus about 1,190 weekly pages** ([1985](https://los40.com/lista40/numeros-1/1985)).

Two quirks matter for the downloader. First, a date that is not a Saturday, or one in the future, returns HTTP 200 with an empty list, never a 404. Second, each row carries a **YouTube video link and an Apple Music track ID**, which is a large head start for matching songs ([2012-06-02](https://los40.com/lista40/listas-anteriores/2012-06-02)). A GitHub repository holds the 2005 to mid-2020 lists as CSV files, but it has no licence and adds nothing the official site lacks ([repo](https://github.com/requeteserrano/evolution-music-taste-spain)).

The list measures radio taste and editorial choice, not sales:

- **February 1967 to April 1971:** the top 10 was set equal to SER's Superventas sales list ([Listas de Éxitos](http://listasexitos.blogspot.com/2016/01/blog-post.html)). Those number ones would be counted twice if they were added to a sales chart's.
- **Today:** the number one is decided by listener votes by phone and on the web ([es.wikipedia Los 40](https://es.wikipedia.org/wiki/Los_40_(Espa%C3%B1a))).
- **Year-end:** LOS40 publishes no year-end ranking for Spain.

Full lists from before 2004 survive only in pieces. Scans of ABC's "Los cuarenta principales" page cover 1981–84 (about 140 PDFs), and JPG scans cover parts of 1969–75 and 1987–90 ([Discomanía](https://revistadiscomania.wordpress.com/los-40-principales-1981-1984/)). Fans transcribed February 1986 to May 1987 ([richi1975](http://richi1975.blogspot.com/2013/12/lista-1037-de-40-principales-2-de.html)), and there are Scribd spreadsheets for 1983 and 1985 ([Scribd](https://es.scribd.com/document/589367034/Listas-de-40-1985)). Other Spanish stations have almost no history online. Cadena 100's "Hot 100" survives in a handful of Wayback snapshots from 2006–07 ([Wayback](https://web.archive.org/web/20061205073049/http://www.cadena100.es/hot100.php)). Cadena Dial, Europa FM, Kiss FM and Rock FM link no charts on their sites, and the Wayback Machine holds no ranked chart of Europa FM, Kiss FM or Cadena Dial either: only editorial playlists, blog lists and articles (checked from the archived addresses, 2026-10-18).

Legally, LOS40 is stricter than PROMUSICAE. Its legal notice allows viewing "única y exclusivamente, para su uso personal y privado" (solely for personal and private use) and prohibits any reproduction ([Aviso legal](https://los40.com/aviso-legal/)). Every page footer also reserves text and data mining under art. 67.3 of RDL 24/2021 ([LOS40 Lista](https://los40.com/lista40/)). robots.txt does not block `/lista40/` and sets no Crawl-delay ([robots.txt](https://los40.com/robots.txt)). A private home copy is the most defensible reading, but it is not a safe harbour. The clean route is a licence request to ventacontenidos@prisamedia.com.

For streaming, **kworb.net** is the practical source. A single page, `es_weekly_totals.html`, summarises every song on Spotify Spain's weekly chart from **28 April 2013 to 15 October 2026**: about 7,460 rows with weeks on chart, weeks in the Top 10, peak and total streams. Its robots.txt allows everything ([kworb totals](https://kworb.net/spotify/country/es_weekly_totals.html); [robots.txt](https://kworb.net/robots.txt)). Spotify's own Spain chart endpoint now returns 401 without a login, and Spotify's User Guidelines ban scraping ([User Guidelines](https://www.spotify.com/us/legal/user-guidelines/)). A Kaggle dataset has daily Top 200 charts for all regions from 2017, last updated February 2022, under an ODbL database licence. Whether it includes Spain was not checked ([Kaggle](https://www.kaggle.com/api/v1/datasets/view/dhruvildave/spotify-charts)).

## Catalonia has one measured chart, and it starts in 2018

The APECAT/BMAT TOP 30 is the only ranked, data-driven chart for Catalonia. BMAT counts plays on 16 stations broadcasting in Catalonia: iCat, Flaixbac, RAC105, Catalunya Música and the Catalan output of Spain-wide networks such as Los 40, Cadena 100 and Europa FM ([Enderrock, summer 2018](https://www.enderrock.cat/noticia/17760/15-cancons-sonat-radio-aquest-estiu)). Whether the station panel has changed since 2018 was not checked.

There are two monthly series:

- **"Llengua catalana"**: songs in Catalan.
- **"Producció catalana"**: songs in any language released by Catalan labels.

The archive page links **99 PDFs of each series**, from September 2018 to September 2026, with year-end lists for 2019 and 2021–2025 ([APECAT llistes](https://apecat.com/ca/llistes-musica-catalunya/)). Each PDF gives places 1–30, the previous month's place, title, artist and label, but no play counts. Each has a text layer and states the dates it measured, for example 14.08.2026–10.09.2026 ([Sept 2026 PDF](https://apecat.com/wp-content/uploads/2026/09/BMAT-APECAT-Top30-setembre-LlenguaCatalana.pdf)). The file names change from year to year, so the links must be taken from the archive page. The 2020 year-end PDF is missing, though Enderrock reported its top four ([Enderrock](https://www.enderrock.cat/noticia/23051/cancons-catala-escoltades-spotify-2020)). APECAT's robots.txt blocks only admin paths, and its legal notice is silent on reusing the chart data ([avís legal](https://apecat.com/ca/avis-legal-i-privacitat/)).

Before 2018 the record is thin and largely made after the fact:

- **1960s–1970s:** no period hit list specific to Catalonia or Catalan music was found. Catalan songs appear only on Spain-wide charts, such as Serrat's "Cançó de matinada", number one in Spain in 1967 ([Viquipèdia, Nova Cançó](https://ca.wikipedia.org/wiki/Nova_Can%C3%A7%C3%B3)).
- **1980s:** the one ranked item found is the **RKOR "Èxits d'Or 86"** listener poll, which ranks ten Catalan songs ([El Temps 1987](https://www.eltemps.cat/documents/el-temps_1987_04_0145_0072_0073.pdf)).
- **1979 onwards, awards only:** the Premi Disc Català de l'Any (albums, from 1979), the Premis Enderrock (from 1994, with best-song categories decided partly by popular vote) and the Premi Cerverí for lyrics (from 1995). Viquipèdia tabulates them ([Premis Enderrock](https://ca.wikipedia.org/wiki/Premis_Enderrock); [Disc Català](https://ca.wikipedia.org/wiki/Premi_Disc_Catal%C3%A0_de_l%27Any)).
- **Flaixbac:** a weekly 45-place countdown, "La Llista Flaixbac", but no archive was found, and the site sits behind a Cloudflare challenge that blocks scripts ([Viquipèdia, Flaixbac](https://ca.wikipedia.org/wiki/R%C3%A0dio_Flaixbac)).

From 2017 the streaming-era lists start to fill in:

- **Enderrock's "Top 100 videoclips en català a YouTube"**, with view counts, for 2017 and 2019–2024 ([2024](https://www.enderrock.cat/noticia/29008/top-100-videoclips-catala-youtube-2024)). Enderrock's news text is CC BY-NC-ND 3.0 ([avís legal](https://www.enderrock.cat/avislegal)).
- **The Anuari de la Música's audited Spotify top 20s** of Catalan songs released each year, from 2020 ([Enderrock](https://www.enderrock.cat/noticia/23051/cancons-catala-escoltades-spotify-2020)).
- **A Viquipèdia table of the 100 Catalan-language songs with the most Spotify plays**, last updated December 2024 and reaching back to 1974 ([Viquipèdia](https://ca.wikipedia.org/wiki/Can%C3%A7ons_en_catal%C3%A0_amb_m%C3%A9s_reproduccions_a_Spotify)).
- **Spotify's weekly Barcelona city chart**, which has history only from autumn 2021, needs a login, and is covered by Spotify's ban on scraping ([3Cat](https://www.3cat.cat/3catinfo/la-marina-sta-morena-ho-trenca-entre-les-top-10-mes-escoltades-de-spotify-a-barcelona/noticia/3311308/)).

This bears on the definition of `catalan`. Its "popular in Catalonia" half has almost no data. In Spotify Wrapped 2024 the top song in Catalonia was Karol G's, and no Catalan-language artist appeared ([Nació Digital](https://naciodigital.cat/next/entreteniment/spotify-revela-quins-son-artistes-cancons-mes-escoltades-catalans-ni-rastre-catala.html)). The only measured "any language" source is APECAT's Producció catalana series, and it covers only Catalan labels. In practice `catalan` will be a Catalan-language score. Copying Spain's chart into it would make the two regions nearly identical.

## The sources at a glance: years, depth, terms and pace

The pace column gives the polite gap between requests. None of these sites publishes a Crawl-delay except Kiss FM (10 s) and the Generalitat data portal (1 s), and neither holds chart data. Where no figure is published, the gap is a courtesy choice for a single paced run whose results are cached.

| Source | Region | Years | What it gives | Size | Licence / terms | Format and access | Polite pace |
|---|---|---|---|---|---|---|---|
| spanishcharts.com weekly singles | spain | 30/12/2001–2026 (2002–04 load by URL only) | Weekly places; per-song runs; number ones from 2005 | 20 (to 2008), 50 (2009–14), 100 (2015–) | "© PROMUSICAE & AGEDI"; Hung Medien all rights reserved; `ai-train=no` | HTML, `weekchart.asp?cat=s&date=YYYYMMDD` (Sunday dates); about 1,290 pages | 5 s; Cloudflare in front; about 1.8 h |
| El Portal de Música | spain | Week 34 of 2009–2026; year-end 2009–2025 | Weekly places, peak, weeks on chart; year-end; Top 100 Streaming; Top 50 Radios (BMAT airplay) | 50 then 100 | Strictly private use allowed; otherwise written permission | HTML, `/lists/top-100-canciones/{Y}/{W}`; about 907 pages | 5–10 s; robots allows everything |
| promusicae.es PDFs | spain | Singles 2004–08; Canciones 2008–2026; streaming 2013–14; year-end 2004–25 | Weekly places, peak, weeks on chart; year-end | 20 / about 40 (2008) / 50 / 100 | Strictly private use allowed; "Prohibida la reproducción" | PDF, IDs from a POST filter form; `pdftotext -layout`; about 1,300 files | 5–10 s; Sucuri firewall; no robots.txt |
| los40.com Lista | spain | Number ones 16/07/1966–2003; full lists 03/01/2004–2026 | Weekly places, weeks on chart, best place; YouTube and Apple IDs on each row | 40 (one row before 2004) | Personal and private viewing only; text-and-data-mining reservation (RDL 24/2021 art. 67.3) | HTML; Saturday dates; empty page means no list; `numeros-1/YYYY` year pages | 5–10 s; about 1,250 requests, about 3.5 h at 10 s |
| kworb.net Spotify Spain totals | spain | 28/04/2013–15/10/2026 | Per song: weeks, weeks in Top 10, peak, streams | Top 200 chart; about 7,460 songs | Spotify data; kworb terms not read | One 2 MB HTML page | 1 request |
| Wikipedia EN number ones | spain | 1959–2026 | Weekly number ones (Salaverri to about 1995) | 1 | CC BY-SA 4.0 | Wikitext via `action=raw`; about 68 pages | Serial requests, descriptive User-Agent; 5–10 s avoided the 429s seen |
| Wikipedia ES weekly Top 10 | spain | 1982–1996 | Weekly places, unsourced ("AFYVE") | 10 | CC BY-SA 4.0 | Wikitext; 15 pages | As above |
| Wikipedia ES Los 40 number ones | spain | 1966–2026 | Weekly number ones (row spans to expand) | 1 | CC BY-SA 4.0 | 61 year pages and 7 decade pages | As above |
| Discomanía "Clasificación Nacional" | spain | 1960–2016 number ones; Top 20 PDFs mainly 1960–65 | Number ones with a named source; about 280 Top 20s for 1960–65 | 1 / 20 | No licence stated | One page plus 404 PDFs | 5 s; WordPress.com robots allows |
| Discomanía / fan blogs, Los 40 scans | spain | 1981–84 (ABC), parts of 1969–75 and 1986–90 | Full Los 40 lists | 40 | ABC and SER rights; no licence | PDF and JPG scans, blog posts; OCR or hand entry | 5 s |
| Salaverri, *Sólo éxitos* | spain | 1959–2002 (2nd ed. to 2012) | Per song per year: peak and weeks on chart | More than 10,000 titles | Print; LPI 135.1.a allows private extraction | Book; hand entry | Not applicable |
| Billboard "Hits of the World" | spain | 1970s (1972 and 1977 checked) | Top 10 | 10 | Billboard copyright | Issue PDFs, about 13 MB, `/Archive-All-Music/` allowed; OCR | Slow, by hand |
| Kaggle Spotify charts | spain (not checked) | 2017–early 2022 | Daily Top 200 | 200 | ODbL database; contents © | 3.5 GB; Kaggle account | 1 download |
| APECAT/BMAT TOP 30 Llengua catalana | catalan | Sept 2018–Sept 2026; year-end 2019, 2021–25 | Monthly places, previous month; year-end | 30 | No licence; terms silent on data | 99 PDFs with a text layer; links taken from the archive page | 2–3 s; about 5 min |
| APECAT/BMAT TOP 30 Producció catalana | catalan | Same | Same, any language, Catalan labels | 30 | Same | 99 PDFs | Same |
| Enderrock.cat lists | catalan | YouTube top 100 2017, 2019–24; Spotify lists; APECAT summaries | Year-end ranks with views or plays | 100 / 10–20 | CC BY-NC-ND 3.0 | HTML articles, `/noticia/{id}/`; no API | 2–3 s; robots has no rules |
| Viquipèdia Spotify top 100 | catalan | Snapshot Dec 2024; songs from 1974–2024 | Cumulative Spotify plays | 100 | CC BY-SA 4.0 | One page via the API | Serial requests |
| Viquipèdia award lists | catalan | Disc Català 1979–2024; Enderrock 1994–2023; Cerverí 1995– | Winners only | 1–3 a year | CC BY-SA 4.0 | A few pages | Serial requests |
| RKOR Èxits d'Or 86 (El Temps) | catalan | 1986 | Ranked listener poll | 10 Catalan songs | Terms not checked | One PDF | 1 request |
| Spotify Barcelona city chart | catalan | Autumn 2021– | Weekly places | 100 | Scraping banned; login needed | Manual lookup only | Not applicable |
| Flaixbac "La Llista" | catalan | About 1994– (not confirmed) | Weekly countdown, partly voted | 45 | Unknown | No archive found; Cloudflare | Not applicable |

## Gaps cluster before 2002 in Spain and before 2018 in Catalonia

The table below shows, for each decade, the best signal that can be downloaded and what is missing. Coverage for `spain` improves in steps, at 1982, 2002 and 2004. For `catalan` it is essentially empty until 2017, then good.

| Decade | `spain`: best downloadable signal | `spain`: gap | `catalan`: best signal | `catalan`: gap |
|---|---|---|---|---|
| 1960s | Weekly or fortnightly sales number ones from 1959; Top 20 PDFs 1960–65; Los 40 number ones from July 1966 | No places 1966–69; magazine and radio lists, not audited sales | Spain-wide charts filtered to Catalan songs ("Cançó de matinada", 1967) | No ranked Catalan list; later "best of" lists only, mostly in print |
| 1970s | Sales and Los 40 number ones every week | Nothing below number one as data; Billboard Top 10 and El Gran Musical monthly scans only | Spain-wide charts filtered; Disc Català de l'Any from 1979 (albums) | No ranked source at all |
| 1980s | Weekly Top 10 from 1982 (es.wiki, unsourced); number ones; Los 40 scans for 1981–84 and 1986–87 | 1980–81 sales places; Top 10 accuracy not verified | RKOR poll 1986 | Nine of ten years have no ranking |
| 1990s | Weekly Top 10 1990–96; number ones (sales and Los 40) | **1997–1999 number ones only**; the AFYVE Top 20 is lost (deleted blog) | Premis Enderrock from 1994; Cerverí from 1995 | Flaixbac's weekly list exists on air but has no archive |
| 2000s | **Weekly Top 20 from 30/12/2001**; Los 40 full lists from 2004; Top 50 from 2009 | 2000–01 number ones only | Awards; Sona9; Catalan records noted in the Spain chart | No Catalan chart |
| 2010s | Full weekly Top 50 then Top 100; Los 40 full lists; Spotify Spain from April 2013 | None significant | APECAT from Sept 2018; Enderrock YouTube 2017, 2019; Viquipèdia Spotify table | 2010 to mid-2018 has no measured ranking |
| 2020s | Full weekly Top 100, Los 40, kworb Spotify to Oct 2026 | Spotify's own country charts need a login | APECAT monthly to Sept 2026; Anuari Spotify top 20s; Enderrock YouTube to 2024 | "Popular in Catalonia, any language" only through Spotify Barcelona (manual) |

## MusicBrainz and Wikidata match songs but rarely hold Catalan IDs

MusicBrainz is the stronger matcher. Its live search found the right recording for every title and artist tested. Its core data is CC0 and comes as a full dump twice a week (`mbdump.tar.bz2`, about 7 GB), while the derived data (tags, ratings) is CC BY-NC-SA ([Download](https://musicbrainz.org/doc/MusicBrainz_Database/Download)).

The API allows **about 1 request per second per IP**. Going faster makes every request fail with 503. It also needs a User-Agent of the form `App/version ( contact )`. The default agent of `musicbrainzngs`, whose last release was in 2020, is on the throttled list ([Rate Limiting](https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting)).

Recording search takes a Lucene query. The fields that matter here:

- `recording`: the title, accent-insensitive by default.
- `recordingaccent`: the title with accents kept.
- `artist`: the full credit, including join phrases.
- `artistname`: any single credited artist.
- `isrc`
- `dur`: duration in milliseconds.

([Search](https://musicbrainz.org/doc/MusicBrainz_API/Search))

Duplicates are the main risk. "Despacito" by Luis Fonsi returned three recordings scoring 100, and only one had an ISRC. "Tusa" returned a DJ-mix compilation recording at score 100 ([search](https://musicbrainz.org/ws/2/recording?query=recording:%22Tusa%22%20AND%20artistname:%22Karol%20G%22&fmt=json)).

MusicBrainz links Spotify tracks to recordings as "free streaming" relationships, but coverage for local acts is poor. The Catalan band Oques Grasses has Spotify, Tidal and Wikidata links at artist level, yet none of its 75 recordings has a URL link and only two have ISRCs. The official "Despacito" video is not in MusicBrainz at all ([artist lookup](https://musicbrainz.org/ws/2/artist/5958db32-246c-495e-beb0-44e55d4666e6?inc=url-rels&fmt=json)). Artist searches with `country:ES` return 22,506 artists. `area:Catalunya` returns 511, an undercount, because it misses artists whose area is a Catalan city such as Barcelona. ListenBrainz's fuzzy "canonical recording" lookup now requires a free user token.

Wikidata (CC0) has every identifier property needed: P1651 for YouTube, P2207 for Spotify tracks, P1902 for Spotify artists, and P434/P4404/P435 for MusicBrainz. Its song coverage is thin, though:

- **Catalan:** only 103 song-type items carry language Catalan, and 11 of them have a YouTube ID and one a Spotify ID.
- **Spanish:** 3,744 such items.
- **All languages:** only **6,269 single, song or musical-work items have a Spotify track ID**.
- **Scattered identifiers:** one song's IDs are spread across separate work, track and music-video items. "Despacito" has four items, with the YouTube ID on the video item and the Spotify ID on the track item ([WDQS](https://query.wikidata.org/)).
- **Looking by performer finds more:** 729 items have a performer who speaks Catalan, 262 of them with a YouTube ID.

The query service gives each client 60 seconds of processing per minute, 5 parallel queries and 30 failed queries per minute. Large queries time out at 60 s, and splitting them fixed every timeout seen ([User Manual](https://www.mediawiki.org/wiki/Wikidata_Query_Service/User_Manual)). The query engine is due to move to a new database by summer 2027, so the SPARQL may need rewriting ([Signpost](https://signpost.news/2026-02-17/Technology_report)). The reconciliation API at wikidata-reconciliation.wmcloud.org accepts a title plus a performer and returned the right items for "Tusa" and "Despacito".

These limits suggest an order of work. Start with the IDs the charts already carry: Los 40's YouTube and Apple IDs, 2004–2026. Next, search Spotify by track and artist with `market=ES` to get the track ID and the ISRC. Spotify restored the ISRC (`external_ids`) in March 2026 after removing it in February ([changelog](https://developer.spotify.com/documentation/web-api/references/changes/march-2026)). Then run a MusicBrainz `isrc:` search, falling back to text search, to get the recording ID. Use Wikidata last, starting from the performer, for any P1651. Before comparing titles, normalise them: remove accents, unify the Catalan "l·l", split artists on feat./con/amb/&/x, and strip version tags such as (Remix) or (Acústico), keeping them as a flag.

## Spotify gives IDs but no popularity; YouTube allows 100 searches a day

The Spotify Web API still works for a personal app, under tighter terms.

- **Access:** since February/March 2026, Development Mode apps need an owner with **Spotify Premium**, allow 5 users, and can use client credentials for search ([migration guide](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide)).
- **Narrower endpoints:** search returns at most 10 results per call, batch `GET /tracks` is gone, and the `popularity` field was removed from tracks and artists. The reference still lists `popularity` but marks it deprecated ([Get Track](https://developer.spotify.com/documentation/web-api/reference/get-track)).
- **No ranking data:** there is no play count, so the API cannot supply a popularity score. It can supply IDs and ISRCs.
- **Rate limit:** counted over a rolling 30-second window, with no published number ([rate limits](https://developer.spotify.com/documentation/web-api/concepts/rate-limits)). About one call per second is a safe guess.
- **Storage and training:** the Developer Terms forbid storing Spotify content indefinitely, building databases of it beyond what is strictly necessary, and using it to train ML or AI models ([Developer Terms](https://developer.spotify.com/terms)). Keeping track IDs as cross-reference keys is the defensible use.

The YouTube Data API v3 gives each project **10,000 units a day**, where a `videos.list` call costs 1 unit. Since 1 June 2026, `search.list` has its own bucket of **100 calls a day** at 1 unit each, and since 3 June a new `videos.batchGetStats` method has a bucket of its own ([quota costs](https://developers.google.com/youtube/v3/determine_quota_cost); [revision history](https://developers.google.com/youtube/v3/revision_history)). Search was already the bottleneck before June, when one search cost 100 of the 10,000 units, so the June change mainly frees the general bucket.

For the later YouTube-views phase, this means 10,000 songs without a known video ID would take 100 days of searching. That is why the IDs that come free with the chart data matter: Los 40's rows, Wikidata's P1651, and the Enderrock clip lists.

The storage rule matters more than the quota. Statistics fetched as non-authorized data must not be kept more than **30 days**, and derived metrics may not stand in for API data ([Developer Policies](https://developers.google.com/youtube/terms/developer-policies)). A video ID is an identifier and can be kept. View counts must be refreshed or deleted within 30 days. Refreshing is cheap, since `videos.list` accepts many IDs per unit (50 per call by long-standing documentation, not re-checked). Whether a stored popularity score computed from views counts as a forbidden "derived metric" is unresolved. The conservative design recomputes it from views fetched within the last 30 days.

## Adapting the formula: one reference chart size and calibrated stand-ins

The current formula scores each week by place relative to the chart's own size N, raised to the 8th power, and that breaks down when chart sizes change. Under that rule, number 10 in a Top 20 earns (11/20)^8 = **0.008**, while number 10 in a Top 100 earns (91/100)^8 = **0.47**. A top-10 hit from 2005 would then score like an also-ran next to one from 2015. The fix is to score every national chart against a **reference size of 100**, using its actual place r, so that 0.008 becomes 0.47 and number 1 is worth 1.0 in every era. Under that exponent a smaller chart loses little. Places 51–100 earn under 0.005 a week, so a Top 50 is almost equivalent to a Top 100. A Top 20 loses only the weeks spent at 21–50, which are worth 0.17 or less each. The same reference size works for the Los 40 Top 40, the APECAT Top 30 and the Wikipedia Top 10s. For kworb's Top 200, places beyond 100 score 0.

Sources without weekly places need stand-ins. All of them can be calibrated on the 2002–2026 data, where full runs exist:

- **Monthly lists (APECAT):** multiply each month's points by the days it measured divided by 7, about 4. The S sum then builds up at the same rate as for a weekly chart.
- **Number ones only (sales 1959–2001, Los 40 1966–2003):** set peak = 1 and S = c × weeks at number one. Take c as the median S per week at number one among songs that reached number one in the full-data era of the same chart. Count fortnightly entries (Discomanía 1960–62) as two weeks. This is an approximation. Turnover changed a lot: in the 1970s a Los 40 number one stayed until it was out-voted, while from 2005 songs stayed 30–40 weeks ([El declive de los 40](https://eldeclivedelos40.blogspot.com/2009/10/evolucion-historica-de-la-lista-de-los.html)). So c should be checked against the 1982–96 Top 10 years, where both kinds of data exist.
- **Peak and weeks only (Salaverri, kworb totals, spanishcharts song pages):** fit S from peak and weeks, plus weeks in the Top 10 where given, by a simple regression on full-run songs.
- **Year-end lists:** for years that also have weekly or monthly data, use them only as a check. Where they stand alone, as with the Enderrock YouTube top 100s and the Anuari Spotify top 20s, which carry view and play counts, they are better used to calibrate the YouTube-views model for Catalan songs than as chart scores.
- **Awards:** treat as a "notable" flag, not as popularity.

Because sources overlap, a region's score should be the **maximum over its sources**, not the sum. PROMUSICAE's Top 100 already includes Spotify, and Los 40's 1967–71 top 10 copied the Superventas list. Each score should keep its source and an era label ("measured", "number ones only", "unverified" for the es.wiki Top 10s, "reconstructed" for pre-2018 `catalan`). That way the later YouTube inference can tell a song that scored 0 on a full chart from one that was simply never observed.

## Download order: five sources cover most of the signal

**First**, the Spain weekly chart for 2002–2026. spanishcharts.com is the single-parser route: about 1,290 pages at 5 s, about 1.8 hours. If Cloudflare challenges the script, El Portal (2009–) and the promusicae.es PDFs (2004–) are the fallback, and their terms explicitly permit private use.

**Second**, los40.com: 61 year pages and about 1,190 weekly pages at 10 s, about 3.5 hours. This is the only Spain radio signal, and its rows carry YouTube IDs. The terms risk here is the highest of the five, given SER's text-and-data-mining reservation.

**Third**, kworb's Spotify Spain totals page: one request.

**Fourth**, the 198 APECAT PDFs at 2–3 s, about ten minutes. This is the whole measured `catalan` signal.

**Fifth**, the Wikipedia pages: EN number ones for 1959–2001, ES weekly Top 10s for 1982–1996, and the Viquipèdia Spotify table. That is about 60 pages, fetched one at a time with a descriptive User-Agent, under CC BY-SA, the cleanest licence of the five.

The second wave:

- Discomanía's 1960–65 Top 20 PDFs (about 280 files).
- The PROMUSICAE year-end PDFs.
- El Portal's Top 50 Radios, once its years are checked.
- The Enderrock YouTube and Spotify lists.

Leave hand work for last: Salaverri's book, the ABC and Billboard scans, and a Wayback search for the deleted AFYVE blog and Flaixbac's list. The Wayback Machine went offline during this research and is reported to allow about 15 CDX requests a minute.

All of these fit one resumable design:

- **Raw first:** store each raw response keyed by URL before parsing.
- **Empty is not missing:** treat an empty Los 40 page as "no list", not as a failure.
- **Back off, don't retry:** on a Cloudflare, Sucuri or "Temporarily Offline" page, stop and wait instead of retrying.
- **Honour 429:** follow Retry-After.
- **Honest User-Agent:** send a descriptive one with a contact address, never a copied browser string.

## Conclusion

The asymmetry between the regions is structural, not a gap in this research. Spain had a commercial chart industry and a dominant radio countdown whose archives went online. Catalonia's Catalan-language music had neither until APECAT commissioned BMAT in 2018. So `catalan` before 2018 cannot be measured from period data; it can only be reconstructed, and the YouTube-views phase will carry most of that weight. That changes what the phase is for. For Spain it fills in the songs that peaked below number one between 1959 and 2001. For Catalonia it is the main signal for four decades. The Enderrock clip lists, with their view counts, are the natural training set for it.

The second lesson concerns the formula, not the data. A steep place weighting tied to each chart's own size silently rewards eras with bigger charts. Fixing the reference size and calibrating number-one-only and peak-only stand-ins against 2002–2026 makes 60 years of mixed sources comparable. Keeping the source and era labels with every score keeps the reconstructed numbers from passing as measured ones.

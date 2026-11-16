"""Add specialized category movies: Anime, New Releases, History, Romance, Action, etc."""
import os
import time
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get("TMDB_API_KEY", "").strip()
CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "movies.csv")

NEW_MOVIES = [
    # Anime
    {
        "title": "Howl's Moving Castle",
        "year": 2004,
        "genres": "Animation, Adventure, Family, Fantasy, Romance",
        "director": "Hayao Miyazaki",
        "cast": "Chieko Baishô, Takuya Kimura, Akihiro Miwa, Tatsuya Gashûin",
        "rating": 8.2,
        "votes": 450000,
        "runtime": 119,
        "moods": "Magical, Whimsical, Romantic, Gorgeous",
        "tagline": "The two lived there.",
        "overview": "When an unconfident young woman is cursed with an old body by a spiteful witch, her only chance of breaking the spell lies with a self-indulgent yet insecure young wizard and his companions in his legged, walking castle.",
        "keywords": "anime, studio ghibli, moving castle, wizard howl, calcifer fire demon, curse of old age, anti-war message"
    },
    {
        "title": "Akira",
        "year": 1988,
        "genres": "Animation, Action, Sci-Fi",
        "director": "Katsuhiro Otomo",
        "cast": "Mitsuo Iwata, Nozomu Sasaki, Mami Koyama, Tesshô Genda",
        "rating": 8.0,
        "votes": 200000,
        "runtime": 124,
        "moods": "Cyberpunk, Mind-Bending, Visceral, Masterpiece",
        "tagline": "Neo-Tokyo is about to E.X.P.L.O.D.E.",
        "overview": "A secret military project endangers Neo-Tokyo when it turns a biker gang member into a rampaging psychic psychopath who can only be stopped by a teenager, his former best friend, and a group of psychics.",
        "keywords": "anime, cyberpunk, neo-tokyo, psychic powers, kaneda red bike slide, tetsuo mutation, apocalyptic sci-fi"
    },
    {
        "title": "A Silent Voice",
        "year": 2016,
        "genres": "Animation, Drama, Romance",
        "director": "Naoko Yamada",
        "cast": "Miyu Irino, Saori Hayami, Aoi Yuki, Kensho Ono",
        "rating": 8.1,
        "votes": 190000,
        "runtime": 130,
        "moods": "Tearjerker, Heartfelt, Emotional, Poignant",
        "tagline": "The shape of voice.",
        "overview": "A young man is ostracized by his classmates after he bullies a deaf girl to the point that she moves away. Years later, he sets off on a path for redemption and seeks to make amends.",
        "keywords": "anime, redemption, sign language, deaf student, bullying guilt, carp pond bread feeding, emotional healing"
    },
    {
        "title": "Ghost in the Shell",
        "year": 1995,
        "genres": "Animation, Action, Crime, Sci-Fi",
        "director": "Mamoru Oshii",
        "cast": "Atsuko Tanaka, Akio Ôtsuka, Iemasa Kayumi, Kôichi Yamadera",
        "rating": 7.9,
        "votes": 160000,
        "runtime": 83,
        "moods": "Cyberpunk, Philosophical, Atmospheric, Visionary",
        "tagline": "It found a voice... now it needs a body.",
        "overview": "In the year 2029, the federal agent Major Motoko Kusanagi and Section 9 hunt a mysterious hacker known as the Puppet Master, questioning her own cybernetic existence and ghost in the machine.",
        "keywords": "anime, cyberpunk, cyborg, puppet master, philosophy of consciousness, thermoptic camouflage, optical invisibility"
    },
    {
        "title": "The Boy and the Heron",
        "year": 2023,
        "genres": "Animation, Adventure, Drama, Family, Fantasy",
        "director": "Hayao Miyazaki",
        "cast": "Soma Santoki, Masaki Suda, Aimyon, Yoshino Kimura",
        "rating": 7.5,
        "votes": 90000,
        "runtime": 124,
        "moods": "Magical, Surreal, Melancholy, Visually Stunning",
        "tagline": "Where death comes to an end, life finds a new beginning.",
        "overview": "In post-WWII Japan, a boy grieving his mother enters a mysterious tower into an enchanted wonderland shared by the living and the dead, guided by a gray heron.",
        "keywords": "anime, studio ghibli, grey heron, grief, warawara, alternate dimension tower, hayao miyazaki finale"
    },
    {
        "title": "Suzume",
        "year": 2022,
        "genres": "Animation, Action, Adventure, Fantasy",
        "director": "Makoto Shinkai",
        "cast": "Nanoka Hara, Hokuto Matsumura, Eri Fukatsu, Shota Sometani",
        "rating": 7.6,
        "votes": 60000,
        "runtime": 122,
        "moods": "Epic, Emotional, Magical, Visually Stunning",
        "tagline": "Closing the doors of disaster.",
        "overview": "A modern action adventure road story where a 17-year-old high school girl named Suzume helps a mysterious young man close mystical doors that are unleashing natural disasters across Japan.",
        "keywords": "anime, earthquake disaster worm, talking three-legged chair, closing mystical doors, road trip across japan, makoto shinkai"
    },
    # New Releases (2023-2024)
    {
        "title": "Killers of the Flower Moon",
        "year": 2023,
        "genres": "Crime, Drama, History",
        "director": "Martin Scorsese",
        "cast": "Leonardo DiCaprio, Robert De Niro, Lily Gladstone, Jesse Plemons, Tantoo Cardinal",
        "rating": 7.6,
        "votes": 250000,
        "runtime": 206,
        "moods": "Haunting, Historical, Gritty, Masterpiece",
        "tagline": "Can you spot the wolves in this picture?",
        "overview": "When oil is discovered in 1920s Oklahoma under Osage Nation land, the Osage people are murdered one by one - until the FBI steps in to unravel the sinister conspiracy.",
        "keywords": "osage nation, oil boom, serial murder conspiracy, fbi investigation, 1920s oklahoma, greed, injustice"
    },
    {
        "title": "Poor Things",
        "year": 2023,
        "genres": "Comedy, Drama, Romance, Sci-Fi",
        "director": "Yorgos Lanthimos",
        "cast": "Emma Stone, Mark Ruffalo, Willem Dafoe, Ramy Youssef, Christopher Abbott",
        "rating": 7.8,
        "votes": 290000,
        "runtime": 141,
        "moods": "Bizarre, Quirky, Visually Stunning, Hilarious",
        "tagline": "She's like nothing you've ever seen.",
        "overview": "The incredible tale about the fantastical evolution of Bella Baxter, a young woman brought back to life by the brilliant and unorthodox scientist Dr. Godwin Baxter, who embarks on a whirlwind adventure across continents.",
        "keywords": "frankenstein fable, female sexual awakening, victorian surrealism, lisbon pastel pastel, godwin baxter, dance sequence"
    },
    {
        "title": "The Holdovers",
        "year": 2023,
        "genres": "Comedy, Drama",
        "director": "Alexander Payne",
        "cast": "Paul Giamatti, Dominic Sessa, Da'Vine Joy Randolph, Carrie Preston",
        "rating": 7.9,
        "votes": 170000,
        "runtime": 133,
        "moods": "Heartwarming, Bittersweet, Cozy, Witty",
        "tagline": "Disreputable, unruly, and unmanageable.",
        "overview": "A cranky history teacher at a New England prep school is forced to remain on campus during Christmas break to babysit the handful of students with nowhere to go, forming an unexpected bond with a damaged student and the grieving head cook.",
        "keywords": "prep school christmas, snowbound campus, unlikely bond, grief, 1970s boston, cherries jubilee, found family"
    },
    {
        "title": "Godzilla Minus One",
        "year": 2023,
        "genres": "Action, Adventure, Drama, Sci-Fi",
        "director": "Takashi Yamazaki",
        "cast": "Ryunosuke Kamiki, Minami Hamabe, Yuki Yamada, Munetaka Aoki",
        "rating": 7.8,
        "votes": 150000,
        "runtime": 124,
        "moods": "Thrilling, Emotional, Epic, Visceral",
        "tagline": "Post-war Japan has lost everything. From zero to minus.",
        "overview": "Post-war Japan is at its lowest point when a gigantic atomic beast emerges, devastating cities and forcing traumatized war veterans to band together with makeshift tactics to defend their homeland.",
        "keywords": "godzilla atomic breath, kamikaze guilt, post-wwii tokyo, minesweeper boat, civilian volunteer fleet, survival"
    },
    {
        "title": "Furiosa: A Mad Max Saga",
        "year": 2024,
        "genres": "Action, Adventure, Sci-Fi",
        "director": "George Miller",
        "cast": "Anya Taylor-Joy, Chris Hemsworth, Tom Burke, Alyla Browne",
        "rating": 7.6,
        "votes": 160000,
        "runtime": 148,
        "moods": "Adrenaline Rush, Epic, Relentless, Visually Stunning",
        "tagline": "Out of the fire she rises.",
        "overview": "The origin story of renegade warrior Furiosa before her encounter and teamup with Mad Max, surviving kidnappings by warlord Dementus and Immortan Joe in the wasteland.",
        "keywords": "mad max wasteland, war rig ambush, dementus chariot bike, sniper rifle duel, vengeance, green place origin"
    },
    {
        "title": "Challengers",
        "year": 2024,
        "genres": "Drama, Romance, Sport",
        "director": "Luca Guadagnino",
        "cast": "Zendaya, Josh O'Connor, Mike Faist, Darnell Appling",
        "rating": 7.2,
        "votes": 120000,
        "runtime": 131,
        "moods": "Electrifying, Tense, Seductive, Energetic",
        "tagline": "Her game. Her rules.",
        "overview": "Tashi, a tennis player turned coach, has transformed her husband into a world-famous grand slam champion. To jolt him out of a losing streak, she enters him into a challenger event against his former best friend and her ex-lover.",
        "keywords": "tennis love triangle, match point tension, reznor ross synth score, competitive ego, sweat and rivalry, churros"
    },
    # History Shows & Films
    {
        "title": "Chernobyl",
        "year": 2019,
        "genres": "Drama, History, Thriller",
        "director": "Johan Renck",
        "cast": "Jared Harris, Stellan Skarsgård, Emily Watson, Paul Ritter, Jessie Buckley",
        "rating": 9.3,
        "votes": 850000,
        "runtime": 330,
        "moods": "Haunting, Gripping, Masterpiece, Harrowing",
        "tagline": "What is the cost of lies?",
        "overview": "In April 1986, an explosion at the Chernobyl nuclear power plant in the Union of Soviet Socialist Republics becomes one of the world's worst man-made catastrophes, told through the heroic men and women who sacrificed everything to contain the disaster.",
        "keywords": "nuclear reactor explosion, radiation poisoning, valery legasov, graphite on roof, soviet bureaucracy, trial truth"
    },
    {
        "title": "Band of Brothers",
        "year": 2001,
        "genres": "Action, Drama, History, War",
        "director": "Phil Alden Robinson, Richard Loncraine",
        "cast": "Damian Lewis, Ron Livingston, Scott Grimes, Donnie Wahlberg, Michael Fassbender",
        "rating": 9.4,
        "votes": 520000,
        "runtime": 600,
        "moods": "Heroic, Tearjerker, Monumental, Masterpiece",
        "tagline": "They depended on each other. And the world depended on them.",
        "overview": "The story of Easy Company of the U.S. Army 101st Airborne Division and their mission in World War II Europe, from Operation Overlord jump to V-J Day, capturing the indomitable bond of soldiers under fire.",
        "keywords": "easy company, paratroopers d-day jump, bastogne battle of bulge winter, dick winters, band of brothers, liberation"
    },
    {
        "title": "1917",
        "year": 2019,
        "genres": "Action, Drama, History, War",
        "director": "Sam Mendes",
        "cast": "George MacKay, Dean-Charles Chapman, Mark Strong, Colin Firth, Benedict Cumberbatch",
        "rating": 8.2,
        "votes": 650000,
        "runtime": 119,
        "moods": "Tense, Visceral, Masterpiece, Relentless",
        "tagline": "Time is the enemy.",
        "overview": "April 6th, 1917. As an infantry battalion assembles to wage war deep in enemy territory, two young British soldiers are assigned to race against time and deliver a message that will stop 1,600 men from walking straight into a deadly trap.",
        "keywords": "world war i trenches, continuous single shot effect, no man's land flare night, race against clock, flares over ruins, brother mission"
    },
    {
        "title": "Braveheart",
        "year": 1995,
        "genres": "Biography, Drama, History, War",
        "director": "Mel Gibson",
        "cast": "Mel Gibson, Sophie Marceau, Patrick McGoohan, Angus Macfadyen",
        "rating": 8.3,
        "votes": 1100000,
        "runtime": 178,
        "moods": "Epic, Heroic, Tearjerker, Masterpiece",
        "tagline": "Every man dies, not every man really lives.",
        "overview": "Scottish warrior William Wallace leads his countrymen in a rebellion to free his homeland from the tyranny of King Edward I of England after the love of his life is murdered.",
        "keywords": "scotland freedom, william wallace blue face warpaint, battle of stirling bridge, bagpipes, rebellion against tyranny"
    },
    {
        "title": "Apollo 13",
        "year": 1995,
        "genres": "Adventure, Drama, History",
        "director": "Ron Howard",
        "cast": "Tom Hanks, Bill Paxton, Kevin Bacon, Gary Sinise, Ed Harris",
        "rating": 7.7,
        "votes": 320000,
        "runtime": 140,
        "moods": "Tense, Inspiring, Gripping, Triumphant",
        "tagline": "Houston, we have a problem.",
        "overview": "NASA must devise a strategy to return Apollo 13 to Earth safely after the spacecraft undergoes massive internal damage in space, threatening the lives of the three astronauts on board.",
        "keywords": "houston we have a problem, oxygen tank explosion, carbon dioxide scrubber duct tape, failure is not an option, lunar module lifeboat"
    },
    {
        "title": "Amadeus",
        "year": 1984,
        "genres": "Biography, Drama, History, Music",
        "director": "Miloš Forman",
        "cast": "F. Murray Abraham, Tom Hulce, Elizabeth Berridge, Roy Dotrice",
        "rating": 8.4,
        "votes": 430000,
        "runtime": 160,
        "moods": "Masterpiece, Jealousy, Magnificent, Tragic",
        "tagline": "Everything you've heard is true.",
        "overview": "The life, success and troubles of Wolfgang Amadeus Mozart, as told by Antonio Salieri, the contemporaneous composer who was deeply jealous of Mozart's God-given musical genius.",
        "keywords": "wolfgang amadeus mozart, antonio salieri jealousy, requiem mass d minor, vienna opera, high-pitched laugh, divine talent"
    },
    # Romance
    {
        "title": "Titanic",
        "year": 1997,
        "genres": "Drama, Romance",
        "director": "James Cameron",
        "cast": "Leonardo DiCaprio, Kate Winslet, Billy Zane, Kathy Bates, Bill Paxton",
        "rating": 7.9,
        "votes": 1300000,
        "runtime": 194,
        "moods": "Epic, Tearjerker, Romantic, Masterpiece",
        "tagline": "Nothing on Earth could come between them.",
        "overview": "A seventeen-year-old aristocrat falls in love with a kind but poor artist aboard the luxurious, ill-fated R.M.S. Titanic.",
        "keywords": "i'm the king of the world, flying on the bow, drawing rose, heart of the ocean, iceberg collision, door floating in freezing water"
    },
    {
        "title": "Pride & Prejudice",
        "year": 2005,
        "genres": "Drama, Romance",
        "director": "Joe Wright",
        "cast": "Keira Knightley, Matthew Macfadyen, Brenda Blethyn, Donald Sutherland, Rosamund Pike",
        "rating": 7.8,
        "votes": 340000,
        "runtime": 129,
        "moods": "Romantic, Witty, Gorgeous, Heartfelt",
        "tagline": "Sometimes the last person on earth you want to be with is the one person you can't be without.",
        "overview": "Sparks fly when spirited Elizabeth Bennet meets single, rich, and proud Mr. Darcy. But Mr. Darcy reluctantly finds himself falling in love with a woman beneath his class.",
        "keywords": "mr darcy hand flex, rain confession, pemberley estate, elizabeth bennet, period romance, jane austen"
    },
    {
        "title": "About Time",
        "year": 2013,
        "genres": "Comedy, Drama, Fantasy, Romance",
        "director": "Richard Curtis",
        "cast": "Domhnall Gleeson, Rachel McAdams, Bill Nighy, Lydia Wilson, Margot Robbie",
        "rating": 7.8,
        "votes": 390000,
        "runtime": 123,
        "moods": "Heartwarming, Tearjerker, Romantic, Life-Affirming",
        "tagline": "What if every moment in life came with a second chance?",
        "overview": "At the age of 21, Tim discovers he can travel in time and change what happens and has happened in his own life. His decision to make his world a better place by getting a girlfriend turns out not to be as easy as you might think.",
        "keywords": "time travel family gift, father son beach walk, underground subway busking romance, red wedding dress in rain, cherish each day"
    },
    {
        "title": "(500) Days of Summer",
        "year": 2009,
        "genres": "Comedy, Drama, Romance",
        "director": "Marc Webb",
        "cast": "Joseph Gordon-Levitt, Zooey Deschanel, Geoffrey Arend, Chloë Grace Moretz",
        "rating": 7.7,
        "votes": 550000,
        "runtime": 95,
        "moods": "Bittersweet, Witty, Relatable, Realistic Romance",
        "tagline": "This is not a love story. This is a story about love.",
        "overview": "An offbeat romantic comedy about a greeting card writer and hopeless romantic who falls for the woman who doesn't believe true love exists, tracing their relationship through an out-of-order timeline.",
        "keywords": "expectation versus reality split screen, ikea furniture date, the smiths elevator, non-linear romance, heartbreak, autumn"
    }
]

df = pd.read_csv(CSV_PATH)
existing_titles = [t.lower() for t in df["title"].tolist()]
session = requests.Session()

max_id = int(df["id"].max()) if not df.empty else 0
added_count = 0

for item in NEW_MOVIES:
    title = item["title"]
    if title.lower() in existing_titles:
        continue

    max_id += 1
    item["id"] = max_id
    item["box_office"] = "N/A"

    # Query TMDB for official poster, backdrop and trailer
    search_title = title.replace(":", "")
    params = {"api_key": API_KEY, "query": search_title, "include_adult": False}
    if item.get("year"):
        params["year"] = item["year"]

    poster_url = "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=600&auto=format&fit=crop&q=80"
    backdrop_url = "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=1280&auto=format&fit=crop&q=80"
    trailer_url = f"https://www.youtube.com/results?search_query={title.replace(' ', '+')}+trailer"

    if API_KEY:
        try:
            r = session.get("https://api.themoviedb.org/3/search/movie", params=params, timeout=5)
            r.raise_for_status()
            results = r.json().get("results", [])
            if results:
                top_m = results[0]
                tmdb_id = top_m.get("id")
                if top_m.get("poster_path"):
                    poster_url = f"https://image.tmdb.org/t/p/w500{top_m['poster_path']}"
                if top_m.get("backdrop_path"):
                    backdrop_url = f"https://image.tmdb.org/t/p/w1280{top_m['backdrop_path']}"
                if top_m.get("vote_average"):
                    item["rating"] = round(float(top_m["vote_average"]), 1)
                if top_m.get("vote_count"):
                    item["votes"] = int(top_m["vote_count"])

                if tmdb_id:
                    video_response = session.get(
                        f"https://api.themoviedb.org/3/movie/{tmdb_id}/videos",
                        params={"api_key": API_KEY},
                        timeout=5,
                    )
                    video_response.raise_for_status()
                    for video in video_response.json().get("results", []):
                        if video.get("site") == "YouTube" and video.get("type") in ["Trailer", "Teaser"]:
                            trailer_url = f"https://www.youtube.com/watch?v={video.get('key')}"
                            break
            time.sleep(0.06)
        except requests.RequestException as error:
            print(f"TMDB lookup failed for {title}: {error}")

    item["poster_url"] = poster_url
    item["backdrop_url"] = backdrop_url
    item["trailer_url"] = trailer_url

    row_df = pd.DataFrame([item])
    df = pd.concat([df, row_df], ignore_index=True)
    added_count += 1
    print(f"Added [{added_count}] {title} ({item['year']}) with TMDB assets")

df.to_csv(CSV_PATH, index=False)
print(f"Completed! Total catalog is now {len(df)} movies (added {added_count} category titles).")

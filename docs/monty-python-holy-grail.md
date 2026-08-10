---
title: "Monty Python and the Holy Grail: a Mermaid showcase"
author: viewmd
tags: [mermaid, showcase, fun]
status: draft
---

# Monty Python and the Holy Grail: a Mermaid showcase

King Arthur has no horse, only a servant banging two coconut halves together, and yet somehow
still needs an org chart. This file tells the story of the quest for the Holy Grail using ten
different Mermaid diagram types — flowcharts, sequence diagrams, and an ER diagram (the three
kinds viewmd already renders today), and seven more (`gantt`, `journey`, `kanban`, `timeline`,
`block-beta`, `classDiagram`, `gitGraph`) that only exist as proposed issues
([VIEWMD-0032](../issues/VIEWMD-0032-mermaid-gantt-charts.md),
[VIEWMD-0033](../issues/VIEWMD-0033-mermaid-user-journey-diagrams.md),
[VIEWMD-0034](../issues/VIEWMD-0034-mermaid-kanban-diagrams.md),
[VIEWMD-0035](../issues/VIEWMD-0035-mermaid-timeline-diagrams.md),
[VIEWMD-0040](../issues/VIEWMD-0040-mermaid-block-beta-diagrams.md),
[VIEWMD-0041](../issues/VIEWMD-0041-mermaid-class-diagrams.md),
[VIEWMD-0042](../issues/VIEWMD-0042-mermaid-gitgraph-diagrams.md)) so far. Viewing this file with
`./viewmd.sh docs/monty-python-holy-grail.md` today will render the flowchart, sequence, and ER
sections as box-drawing art and raise `UnsupportedDiagramError` on the rest — which is itself
a fitting bit of Grail-quest futility: the fences are there, correctly written, and the
Bridgekeeper still throws you in the gorge.

For the record, before the silliness starts: released in 1975 on a budget of just £282,035, shot
mostly around Doune Castle and Glen Coe in Scotland, and financed in part because rock acts like
Led Zeppelin and Pink Floyd were looking for a tax write-off against Britain's 90% top income tax
rate at the time. The coconuts exist purely because the production couldn't afford real horses —
a budget gag so beloved it gave the film its German title, *Die Ritter der Kokosnuß* ("The Knights
of the Coconut"). It turned 50 in 2025, with a Fathom Events theatrical re-release and Terry
Gilliam doing the rounds at festivals to mark it — the source material for this file is at least
that well-tested. (Sources: [Wikipedia](https://en.wikipedia.org/wiki/Monty_Python_and_the_Holy_Grail),
[IMDb](https://www.imdb.com/title/tt0071853/).)

## The quest begins — flowchart

Three men on foot, banging coconuts together, do not simply walk to the Bridge of Death — they
get interrogated by a keeper who lobs the unprepared into the Gorge of Eternal Peril for wrong
answers, and gets lobbed in himself for an unanswerable one:

```mermaid
flowchart TD
    A([Approach the Bridge of Death]) --> B{"What... is your name?"}
    B -->|"Sir Lancelot of Camelot"| C{"What... is your quest?"}
    B -->|hesitates| Z[["CATAPULTED into the Gorge of Eternal Peril"]]
    C -->|"To seek the Holy Grail"| D{"What... is your favourite colour?"}
    C -->|hesitates| Z
    D -->|"Blue! No, yel--"| Z
    D -->|"Blue"| E([Cross the Bridge of Death])
    D -->|"What is the air-speed velocity of an unladen swallow?"| Y{"African or European swallow?"}
    Y -->|"I don't know that!"| F[["Bridgekeeper himself is CATAPULTED"]]
    F --> E
```

Lancelot storms it, Robin bottles the colour question, Galahad nearly makes it and then blows
"blue" at the last syllable, and Arthur turns the question back on the Bridgekeeper — who has no
answer for his own riddle and joins his victims in the gorge.

## The Black Knight — sequence diagram

Widely voted the single funniest scene in the film: Arthur wins a swordfight against an opponent
who refuses, on principle, to acknowledge losing any of his limbs:

```mermaid
sequenceDiagram
    participant Arthur as King Arthur
    participant Knight as Black Knight
    Arthur->>Knight: None shall pass.
    Knight-->>Arthur: I move for no man.
    Arthur->>Knight: (cleaves off his left arm)
    Knight-->>Arthur: 'Tis but a scratch.
    Arthur->>Knight: A scratch?! Your arm's off!
    Knight-->>Arthur: No, it isn't.
    Arthur->>Knight: (cleaves off his right arm)
    Knight-->>Arthur: Just a flesh wound.
    Note right of Knight: Continues fighting <br>with no arms remaining.
    Arthur->>Knight: (cleaves off his left leg)
    Knight-->>Arthur: Right, I'll do you for that!
    Arthur->>Knight: (cleaves off his right leg)
    Knight--xArthur: All right, we'll call it a draw.
    Arthur-->>Knight: Come, Patsy.
    Knight-)Arthur: Oh, oh, I see, running away, eh? <br>Come back here and take what's coming to you! <br>I'll bite your legs off!
```

## French taunting — sequence diagram

Arthur's polite request for a look around the Grail-holding castle meets the finest diplomacy
France has to offer:

```mermaid
sequenceDiagram
    participant Arthur as King Arthur
    participant Guard as French Guard
    Arthur->>Guard: This is Uther Pendragon's son, Arthur, King of the Britons.
    Guard-->>Arthur: I don't want to talk to you no more, you empty-headed animal food-trough wiper.
    Arthur->>Guard: I don't want to talk to you no more, you empty-headed animal food-trough wiper!
    Guard--xArthur: I fart in your general direction!
    Note right of Guard: Your mother was a hamster<br>and your father smelt of elderberries.
    Arthur->>Guard: Is there someone else up there we could talk to?
    Guard-->>Arthur: No, now go away, or I shall taunt you a second time!
    loop the negotiation completely fails
        Arthur->>Guard: We are French! Why do you think we have this outrageous accent, you silly king-a?
        Guard-->>Arthur: (throws a cow over the wall)
    end
    Guard-)Arthur: (fetchez la vache)
```

## The Round Table — entity-relationship diagram

Camelot, contrary to popular myth, is a silly place, and everyone who lives, quests, or gets
turned into a newt there fits neatly into an ER diagram:

```mermaid
erDiagram
    KNIGHT ||--o{ QUEST : undertakes
    KNIGHT {
        string name PK
        string epithet "e.g. the Brave, the Pure"
        int coconutHorses "zero, they migrate"
        boolean sayNiCompliant FK
    }
    KNIGHT }o--|| ROUND_TABLE : "sits at"
    QUEST ||--|{ OBSTACLE : contains
    QUEST {
        string objective PK
        string startingPoint "Camelot (too silly to visit)"
        boolean grailFound "false, always false"
    }
    OBSTACLE {
        string name PK
        string danger "e.g. 'has a wafer-thin mint of a bite radius'"
        boolean isActuallyJustARabbit
    }
    KNIGHT ||--o{ SHRUBBERY : "must produce, on demand"
    KNIGHT 1 to 0+ TAUNT : receives
    TAUNT {
        string phrase "your father smelt of elderberries"
        string deliveredBy "French Guard"
    }
```

## Quest schedule — Gantt chart

Assembling the knights, negotiating with the Knights Who Say Ni, and building a large wooden
badger all take actual calendar time, and somebody has to track it — badly, on a scroll, in a
silly place:

```mermaid
gantt
    title Quest for the Holy Grail
    dateFormat YYYY-MM-DD
    section Recruitment
        Gather Knights of the Round Table :done, rec1, 0932-01-01, 20d
        Acquire coconuts (horses unavailable) :done, rec2, after rec1, 3d
    section Knights Who Say Ni
        Negotiate passage through the forest :active, ni1, after rec2, 5d
        Fetch a shrubbery :ni2, after ni1, 4d
        Cut down the tallest tree with a herring :ni3, after ni2, 2d
        Say "Ekki-ekki-ekki-ptang-zoom-boing" correctly :milestone, ni4, after ni3, 0d
    section Trojan Rabbit
        Build enormous wooden rabbit :tr1, after ni4, 6d
        Forget to hide the knights inside :crit, tr2, after tr1, 1d
        Catapult own rabbit back over the wall :tr3, after tr2, 1d
    section Bridge of Death
        Answer the Bridgekeeper's three questions :bod1, after tr3, 1d
        Debate air-speed velocity of unladen swallows :bod2, after bod1, 1d
        Cross the Bridge of Death :milestone, bod3, after bod2, 0d
    section Cave of Caerbannog
        Underestimate the rabbit :cave1, after bod3, 1d
        Deploy the Holy Hand Grenade of Antioch :cave2, after cave1, 1d
        Count to three (not one, not five) :cave3, after cave2, 1d
```

`crit` and `%%` weekend-exclusion syntax above are deliberately used but out of scope for
[VIEWMD-0032](../issues/VIEWMD-0032-mermaid-gantt-charts.md) as currently written — a `crit,
done`-tagged forgetful rabbit-building step falls back to whichever of `done`/`active` it also
carries, same as any other Mermaid gantt chart.

## Sir Robin's brave day — user journey

Brave Sir Robin ran away, bravely ran away, away — a day better told as a journey than a boast:

```mermaid
journey
    title Sir Robin's Very Brave Day
    section The Three-Headed Knight
      Approach confidently: 4: Robin
      Hear it argue with itself: 3: Robin
      Consider fighting: 2: Robin
      Turn and run: 1: Robin, Minstrels
    section The Enchanter's Cave
      Hear tales of a fearsome rabbit: 3: Robin
      Scoff at a bunny: 4: Robin
      Watch Sir Bors get decapitated: 1: Robin
      Soil oneself slightly: 1: Robin
    section The Retreat
      Gallop home to Camelot: 5: Robin
      Compose a heroic ballad about it anyway: 5: Robin, Minstrels
```

## The Round Table backlog — kanban board

Even a legendary quest runs on a task board, and this one has been blocked on the same column
for three scenes running:

```mermaid
kanban
  Todo
    grail[Find the Holy Grail]
    horse[Acquire an actual horse]
  Blocked by Knights Who Say Ni
    shrub[Bring us a shrubbery]@{ priority: 'High', assigned: 'Sir Robin' }
    tree[Cut down the tallest tree in the forest with a herring]@{ priority: 'Very High', assigned: 'Roger the Shrubber' }
  In progress
    rabbit[Build the Trojan Rabbit]@{ assigned: 'Sir Bedevere' }
    bridge[Answer the Bridgekeeper's questions]@{ priority: 'Critical', assigned: 'King Arthur' }
  Done
    coconut[Establish that swallows carry coconuts]@{ assigned: 'King Arthur', priority: 'Low' }
    ni[Say Ni no more]@{ assigned: 'Roger the Shrubber', priority: 'High' }
  Can't reproduce
    scratch[Black Knight claims 'tis but a scratch]@{ assigned: 'Sir Lancelot' }
```

## A brief history of Camelot — timeline

The legend, condensed, from founding myth to the point where everyone collectively decides it's
a silly place and they won't go there:

```mermaid
timeline
    title A Brief History of Camelot
    section The countryside
        Plague cart round : "Bring out your dead" <br>-- one customer insists <br>he's not dead yet
        Anarcho-syndicalist commune : peasant explains <br>the water-based system <br>of Arthurian legitimacy
    section Founding myth
        The Lady of the Lake : holds aloft Excalibur <br>from the bosom of the water
        King Arthur : is established as king <br>by strange women lying in ponds<br>distributing swords
    section The Quest
        God appears : points at a map, <br>demands a quest for the Grail
        The Knights Who Say Ni : demand a shrubbery, <br>then a second, slightly bigger shrubbery
        The Trojan Rabbit : a badger that is <br>not, strictly, a badger
    section The Verdict
        Camelot itself : universally agreed, <br>on arrival, to be a silly place
```

## Castle Anthrax floor plan — block-beta diagram

Castle Anthrax, home to Zoot, Dingo, and "eight score young blondes and brunettes, all between
sixteen and nineteen-and-a-half," has a floor plan best expressed as blocks:

```mermaid
block-beta
    columns 3
    GATE["Drawbridge"]:3
    HALL["Great Hall<br>(spanking practice)"] TOWER["Zoot's Tower"] DUNGEON["Oscillating Room"]
    KITCHEN["Kitchen<br>(massage oils only)"] COURT["Courtyard"] CHAPEL["Chapel<br>(unused)"]
```

## Bestiary and cast taxonomy — class diagram

A proper taxonomy of who's a knight, who's a rabbit, and who is, strictly speaking, a killer:

```mermaid
classDiagram
    class Knight {
        <<interface>>
        +sayCatchphrase()
        +surviveEncounter() bool
    }
    class KingArthur {
        +int coconutHalvesForHorse
        +sayCatchphrase()
        +surviveEncounter() bool
        +cleaveArmsOff(BlackKnight)
    }
    class SirRobin {
        +int braveryScore
        +runAway()
        +surviveEncounter() bool
    }
    class BlackKnight {
        +int limbsRemaining
        +declareScratch()
        +surviveEncounter() bool
    }
    class KillerRabbit {
        +int bodyCount
        +hop()
        +attack() Fatality
    }
    Knight <|.. KingArthur
    Knight <|.. SirRobin
    Knight <|.. BlackKnight
    BlackKnight <|-- HalfLimblessBlackKnight
    KillerRabbit --> HolyHandGrenade : is defeated by
```

## Branches of the quest — gitGraph

The knights don't quest as one party for long — Arthur splits them up to search separately, and
the timeline branches and merges (badly) right up to the film's famously unresolved ending:

```mermaid
gitGraph
    commit id: "Camelot founded" tag: "too silly to visit"
    commit id: "God appears, demands quest"
    branch trojan-rabbit
    checkout trojan-rabbit
    commit id: "Build enormous wooden rabbit"
    commit id: "Forget knights inside it"
    checkout main
    commit id: "Reach French castle"
    merge trojan-rabbit id: "Catapult own rabbit back over wall"
    branch bridge-of-death
    checkout bridge-of-death
    commit id: "Answer three questions"
    commit id: "Debate swallow velocity"
    checkout main
    merge bridge-of-death id: "Cross successfully"
    commit id: "Police arrive, arrest everyone" tag: "THE END"
```

## Closing note

None of the seven proposed-only sections above render yet — until
[VIEWMD-0032](../issues/VIEWMD-0032-mermaid-gantt-charts.md)–[VIEWMD-0042](../issues/VIEWMD-0042-mermaid-gitgraph-diagrams.md)
land, viewing this file shows the flowchart/sequence/ER art in full and a graceful
`UnsupportedDiagramError` fallback for the rest, which — much like the quest itself — ends not
with a bang, but with a mildly apologetic shrug and a man in a suit turning off the camera.

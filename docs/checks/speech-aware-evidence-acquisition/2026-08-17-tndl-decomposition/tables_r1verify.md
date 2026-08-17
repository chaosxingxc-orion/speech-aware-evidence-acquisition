### Per-class three-way decomposition

| class | group | wrong | FORMAT | PRE-PUB | NOVEL | fmt% | prepub% | novel% | decoy% |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|
| CARDINAL | NUM | 739 | 665 | 58 | 16 | 90.0% | 7.8% | 2.2% | 4.2% |
| DATE | NUM | 349 | 243 | 46 | 60 | 69.6% | 13.2% | 17.2% | 4.6% |
| PERCENT | NUM | 279 | 265 | 11 | 3 | 95.0% | 3.9% | 1.1% | 3.6% |
| YEAR | NUM | 277 | 238 | 37 | 2 | 85.9% | 13.4% | 0.7% | 9.4% |
| ALPHANUMERIC | NUM | 218 | 203 | 4 | 11 | 93.1% | 1.8% | 5.0% | 0.5% |
| CONTRACTION | CONV | 213 | 50 | 54 | 109 | 23.5% | 25.4% | 51.2% | 3.8% |
| ORG | NAME | 184 | 4 | 92 | 88 | 2.2% | 50.0% | 47.8% | 6.0% |
| MONEY | NUM | 175 | 150 | 18 | 7 | 85.7% | 10.3% | 4.0% | 3.4% |
| ABBREVIATION | CONV | 134 | 3 | 62 | 69 | 2.2% | 46.3% | 51.5% | 8.2% |
| PERSON | NAME | 95 | 6 | 61 | 28 | 6.3% | 64.2% | 29.5% | 2.1% |
| GPE | NAME | 71 | 9 | 56 | 6 | 12.7% | 78.9% | 8.5% | 39.4% |
| EVENT | NAME | 35 | 31 | 1 | 3 | 88.6% | 2.9% | 8.6% | 0.0% |
| PRODUCT | NAME | 34 | 16 | 13 | 5 | 47.1% | 38.2% | 14.7% | 0.0% |
| ORDINAL | NUM | 28 | 25 | 2 | 1 | 89.3% | 7.1% | 3.6% | 0.0% |
| FAC | NAME | 9 | 1 | 2 | 6 | 11.1% | 22.2% | 66.7% | 0.0% |
| TIME | NUM | 9 | 5 | 1 | 3 | 55.6% | 11.1% | 33.3% | 0.0% |
| QUANTITY | NUM | 7 | 6 | 0 | 1 | 85.7% | 0.0% | 14.3% | 0.0% |
| WEBSITE | NAME | 6 | 0 | 6 | 0 | 0.0% | 100.0% | 0.0% | 0.0% |
| LOC | NAME | 4 | 1 | 2 | 1 | 25.0% | 50.0% | 25.0% | 0.0% |
| NORP | NAME | 4 | 0 | 0 | 4 | 0.0% | 0.0% | 100.0% | 0.0% |
| WORK_OF_ART | NAME | 2 | 0 | 0 | 2 | 0.0% | 0.0% | 100.0% | 0.0% |
| RANGE | NUM | 1 | 0 | 1 | 0 | 0.0% | 100.0% | 0.0% | 0.0% |
| **NUMERIC total** | | **2082** | **1800** | **178** | **104** | **86.5%** | **8.5%** | **5.0%** | 4.3% |
| **CONVENTION total** | | **347** | **53** | **116** | **178** | **15.3%** | **33.4%** | **51.3%** | 5.5% |
| **NAME total** | | **444** | **68** | **233** | **143** | **15.3%** | **52.5%** | **32.2%** | 9.2% |
| **ALL total** | | **2873** | **1921** | **527** | **425** | **66.9%** | **18.3%** | **14.8%** | 5.2% |

### Per-call

| call | wrong | FORMAT | PRE-PUB | NOVEL | ConEC PDFs |
|---|--:|--:|--:|--:|---|
| 4330115 | 205 | 140 | 59 | 6 | 4330115_1.pdf (212049c), 4330115_2.pdf (39056c) |
| 4365024 | 478 | 315 | 110 | 53 | 4365024_2.pdf (49890c) |
| 4365948 | 280 | 183 | 58 | 39 | 4365948_1.pdf (75797c) |
| 4366429 | 332 | 158 | 77 | 97 | 4366429_1.pdf (38441c), 4366429_2.pdf (63428c) |
| 4366522 | 278 | 151 | 80 | 47 | **none** |
| 4384964 | 261 | 185 | 33 | 43 | 4384964_1.pdf (11556c) |
| 4385072 | 257 | 195 | 18 | 44 | **none** |
| 4387383 | 159 | 120 | 23 | 16 | 4387383_2.pdf (109767c) |
| 4389907 | 170 | 124 | 22 | 24 | 4389907_2.pdf (75602c) |
| 4397829 | 453 | 350 | 47 | 56 | 4397829_1.pdf (44282c), 4397829_2.pdf (55291c) |

### FORMAT examples CAUGHT

The tight window is what the aligner paired with the gold mention; the wide window (+/-6 tokens) is what the match was actually found in.

| # | class | gold mention | hypothesis, tight | hypothesis, wide |
|--:|---|---|---|---|
| 1 | YEAR | `2020` | `twenty` | `welcome to Cult's third quarter twenty twenty earnings conference call. Today's call is` |
| 2 | CARDINAL | `2020` | `twenty` | `welcome to Cult's third quarter twenty twenty earnings conference call. Today's call is` |
| 3 | DATE | `the third quarter of fiscal 2020` | `the third quarter of fiscal two thousand twenty.` | `to review the company's results for the third quarter of fiscal two thousand twenty. As we start, let me state` |
| 4 | ALPHANUMERIC | `10-K` | `ten K` | `company's most recent filings on Form ten K and Form ten Q. You are` |
| 5 | ALPHANUMERIC | `10-Q` | `ten Q.` | `on Form ten K and Form ten Q. You are cautioned not to place` |
| 6 | ALPHANUMERIC | `8-K` | `eight K` | `schedule to the company's press release. eight K filed yesterday and posted on the` |
| 7 | DATE | `fourth quarter fiscal 2020` | `fourth quarter fiscal twenty twenty` | `after that, Ken will review our fourth quarter fiscal twenty twenty business outlook. We will then be` |
| 8 | DATE | `fiscal 2020` | `fiscal twenty twenty,` | `of a diverse customer base. Throughout fiscal twenty twenty, we have maintained our position as` |
| 9 | CARDINAL | `72` | `two` | `third quarter. Net sales were seventy two million, down six point eight percent` |
| 10 | PERCENT | `6.8%` | `eight percent` | `seventy two million, down six point eight percent compared with the prior year period.` |
| 11 | CARDINAL | `5.1` | `point one` | `reported a net loss of five point one million compared with a pre tax` |
| 12 | CARDINAL | `4.3` | `point three` | `a pre tax income of four point three million for the same period last` |

### FORMAT examples NOT caught (surviving as true errors)

| # | class | gold mention | hypothesis, tight | hypothesis, wide |
|--:|---|---|---|---|
| 1 | PERCENT | `120%` | `thirty` | `twenty percent to one hundred and thirty percent range based on the facts` |
| 2 | DATE | `last year` | `last year's` | `seven point four percent compared with last year's third quarter. Operating income for the` |
| 3 | CARDINAL | `quarter` | `quarterly` | `five million to shareholders in regular quarterly dividends and share repurchases through the` |
| 4 | DATE | `the first month of this fiscal year` | `the first nine months of this fiscal year` | `four point seven million respectively for the first nine months of this fiscal year due primarily to the timing of` |
| 5 | ORDINAL | `second` | `thing` | `cases. Okay. And then secondly, um thing for me on the home accessories` |
| 6 | ALPHANUMERIC | `B2B` | `B` | `accessory products on the B to B side. Uh we have a lot` |
| 7 | DATE | `second quarter's 2020` | `second quarter twenty twenty` | `welcome to the Nexstar Media Group second quarter twenty twenty results call. Today's call is being` |
| 8 | CARDINAL | `199` | `five.` | `Litigation Reform Act of nineteen ninety five. Nexstar cautions that these forward-looking` |

### PRE-PUBLISHED examples (numeric)

 1. `PERCENT` gold `120%` keys=['120'] found in [pdf] decoy_hit=True
 2. `DATE` gold `last year` keys=['lastyear'] found in [pdf] decoy_hit=False
 3. `CARDINAL` gold `quarter` keys=['quarter'] found in [biasing_txt,pdf] decoy_hit=False
 4. `ORDINAL` gold `second` keys=['second'] found in [biasing_txt,pdf] decoy_hit=False
 5. `CARDINAL` gold `199` keys=['199'] found in [pdf] decoy_hit=True
 6. `DATE` gold `199` keys=['199'] found in [pdf] decoy_hit=True
 7. `YEAR` gold `199` keys=['199'] found in [pdf] decoy_hit=True
 8. `PERCENT` gold `28%` keys=['28'] found in [pdf] decoy_hit=True
 9. `CARDINAL` gold `201` keys=['201'] found in [pdf] decoy_hit=True
10. `DATE` gold `201` keys=['201'] found in [pdf] decoy_hit=True

### NOVEL examples (numeric)

 1. `DATE` gold `the first month of this fiscal year` -> hypothesis `the first nine months of this fiscal year` keys=['thefirstmonthofthisfiscalyear', 'themonthofthisfiscalyear']
 2. `ALPHANUMERIC` gold `B2B` -> hypothesis `B` keys=['b2b']
 3. `DATE` gold `second quarter's 2020` -> hypothesis `second quarter twenty twenty` keys=['quarters2020', 'secondquarters2020']
 4. `ALPHANUMERIC` gold `10K` -> hypothesis `K` keys=['10000', '10k', '10thousand']
 5. `MONEY` gold `$13.86` -> hypothesis `six cents` keys=['13.86']
 6. `DATE` gold `year end 2019` -> hypothesis `year end twenty twenty one. twenty nineteen,` keys=['yearend2019']
 7. `DATE` gold `December 31 of 202` -> hypothesis `december thirty one of twenty twenty two.` keys=['december31of202']
 8. `TIME` gold `8:00 PM` -> hypothesis `eight p m` keys=['800pm', '80pm']
 9. `TIME` gold `11:00 PM` -> hypothesis `p m E` keys=['1100pm', '110pm']
10. `DATE` gold `September 19th 201` -> hypothesis `September nineteenth twenty nineteen.` keys=['september19th201', 'september201']

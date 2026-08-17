### Per-class three-way decomposition

| class | group | wrong | FORMAT | PRE-PUB | NOVEL | fmt% | prepub% | novel% | decoy% |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|
| CARDINAL | NUM | 724 | 650 | 60 | 14 | 89.8% | 8.3% | 1.9% | 5.0% |
| DATE | NUM | 341 | 242 | 46 | 53 | 71.0% | 13.5% | 15.5% | 5.0% |
| PERCENT | NUM | 275 | 260 | 12 | 3 | 94.5% | 4.4% | 1.1% | 3.6% |
| YEAR | NUM | 271 | 232 | 37 | 2 | 85.6% | 13.7% | 0.7% | 4.4% |
| CONTRACTION | CONV | 214 | 48 | 55 | 111 | 22.4% | 25.7% | 51.9% | 2.3% |
| ALPHANUMERIC | NUM | 202 | 178 | 9 | 15 | 88.1% | 4.5% | 7.4% | 0.5% |
| ORG | NAME | 182 | 3 | 90 | 89 | 1.6% | 49.5% | 48.9% | 6.6% |
| MONEY | NUM | 163 | 137 | 20 | 6 | 84.0% | 12.3% | 3.7% | 3.1% |
| ABBREVIATION | CONV | 145 | 3 | 73 | 69 | 2.1% | 50.3% | 47.6% | 9.7% |
| PERSON | NAME | 97 | 6 | 61 | 30 | 6.2% | 62.9% | 30.9% | 4.1% |
| GPE | NAME | 70 | 10 | 55 | 5 | 14.3% | 78.6% | 7.1% | 40.0% |
| EVENT | NAME | 36 | 31 | 1 | 4 | 86.1% | 2.8% | 11.1% | 0.0% |
| PRODUCT | NAME | 33 | 14 | 12 | 7 | 42.4% | 36.4% | 21.2% | 0.0% |
| ORDINAL | NUM | 28 | 25 | 2 | 1 | 89.3% | 7.1% | 3.6% | 0.0% |
| TIME | NUM | 9 | 5 | 1 | 3 | 55.6% | 11.1% | 33.3% | 0.0% |
| FAC | NAME | 8 | 1 | 2 | 5 | 12.5% | 25.0% | 62.5% | 0.0% |
| QUANTITY | NUM | 7 | 6 | 0 | 1 | 85.7% | 0.0% | 14.3% | 0.0% |
| WEBSITE | NAME | 6 | 0 | 6 | 0 | 0.0% | 100.0% | 0.0% | 0.0% |
| LOC | NAME | 4 | 1 | 2 | 1 | 25.0% | 50.0% | 25.0% | 0.0% |
| NORP | NAME | 4 | 0 | 0 | 4 | 0.0% | 0.0% | 100.0% | 0.0% |
| WORK_OF_ART | NAME | 2 | 0 | 0 | 2 | 0.0% | 0.0% | 100.0% | 0.0% |
| RANGE | NUM | 1 | 0 | 1 | 0 | 0.0% | 100.0% | 0.0% | 0.0% |
| **NUMERIC total** | | **2021** | **1735** | **188** | **98** | **85.8%** | **9.3%** | **4.8%** | 4.0% |
| **CONVENTION total** | | **359** | **51** | **128** | **180** | **14.2%** | **35.7%** | **50.1%** | 5.3% |
| **NAME total** | | **442** | **66** | **229** | **147** | **14.9%** | **51.8%** | **33.3%** | 10.0% |
| **ALL total** | | **2822** | **1852** | **545** | **425** | **65.6%** | **19.3%** | **15.1%** | 5.1% |

### Per-call

| call | wrong | FORMAT | PRE-PUB | NOVEL | ConEC PDFs |
|---|--:|--:|--:|--:|---|
| 4330115 | 204 | 140 | 58 | 6 | 4330115_1.pdf (212049c), 4330115_2.pdf (39056c) |
| 4365024 | 475 | 315 | 107 | 53 | 4365024_2.pdf (49890c) |
| 4365948 | 274 | 177 | 58 | 39 | 4365948_1.pdf (75797c) |
| 4366429 | 351 | 172 | 79 | 100 | 4366429_1.pdf (38441c), 4366429_2.pdf (63428c) |
| 4366522 | 224 | 98 | 80 | 46 | **none** |
| 4384964 | 247 | 167 | 39 | 41 | 4384964_1.pdf (11556c) |
| 4385072 | 245 | 180 | 22 | 43 | **none** |
| 4387383 | 154 | 116 | 23 | 15 | 4387383_2.pdf (109767c) |
| 4389907 | 190 | 133 | 32 | 25 | 4389907_2.pdf (75602c) |
| 4397829 | 458 | 354 | 47 | 57 | 4397829_1.pdf (44282c), 4397829_2.pdf (55291c) |

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
| 5 | ORDINAL | `second` | `thing` | `cases. Okay. And then secondly, um. thing for me on the home accessories` |
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

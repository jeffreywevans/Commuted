#!/usr/bin/env python3
"""Generate a random story brief as Markdown with YAML front matter."""

from __future__ import annotations

import argparse
import math
import random
import re
import secrets
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

TITLES = [
    "A Comfortable Bed in @setting",
    "A Night With Pleasing Bourbon",
    "A Quiet Revolt in @time_period",
    "A Weather of Ash and Gold",
    "Allow Me to Retort!",
    "Bliss-Based Decision-Making",
    "Doubling Up on a Bad Idea",
    "Escape from @setting",
    "Fifty Percent of All People Are Below Average",
    "Gatsby Was a Gangster",
    "Gilley Grazes for Girls",
    "How Many Rubbers Did You Bring?",
    "I Am Right, You Know",
    "I Liked You Better in @setting Before You Got Dressed",
    "I Need You to Know That You Are Stupid",
    "I Retain the Option",
    "If You Want a Friend",
    "It's Never Enough",
    "Let's Do Lunch",
    "Let's Piss Jeff Off!",
    "Let's Piss Kathy Off!",
    "Letters from the Edge of @setting",
    "Local Radio Rocks",
    "No One Leaves @setting Unchanged",
    "Pride, Excellence and a Fifty Dollar Bill",
    "Sampling the Local Nightlife",
    "Sober, Naked and Unafraid",
    "That Is Going to Be Uncomfortable",
    "The Day the Bells Fell Silent",
    "The Easy Way, the Hard Way, and the Commuted Way",
    "The Iron Promise",
    "The Last Good Lie",
    "The Last Lantern of @setting",
    "The Performance Needs Work",
    "The Winter Beneath the Streetlights",
    "They Can Wait!",
    "Trouble Sleeping Alone",
    "What Next?",
    "What's One More Night With These Fools",
    "When @protagonist Broke the Map",
    "Whiskey, Lust and @setting Mix Fine",
    "Who Thought This Was a Good Idea?",
    "You Park Like You Fuck and Deserve the Ticket",
    "You Running for Pope?",
    "You Suck and You Know It",
    "You Want Me to Autograph Your What?",
    "@protagonist at Play",
]

PROTAGONIST_AVAILABILITY = [
    ("Avril Lavigne", 2024, 2032),
    ("Bill Davenport", 1989, 2032),
    ("Cremeans", 1989, 2032),
    ("Gilley", 1989, 2019),
    ("Jeff Evans", 1989, 2032),
    ("Jeremy Evans", 1989, 2032),
    ("Jim Brown", 1989, 2032),
    ("Kathy Espich", 1989, 2011),
    ("Kendall Weatherby", 1998, 2032),
    ("Madeline Quinlan", 2024, 2032),
    ("Sarah Malcolm", 1989, 2025),
]

CHARACTER_AVAILABILITY = PROTAGONIST_AVAILABILITY

DATE_START = date(1989, 12, 4)
DATE_END = date(2032, 8, 8)

SETTING_AVAILABILITY = [
    ("Madison Square Garden – New York, NY, USA", 1993, 2032),
    ("Barclays Center – Brooklyn, NY, USA", 2012, 2032),
    ("UBS Arena – Elmont, NY, USA", 2021, 2032),
    ("Prudential Center – Newark, NJ, USA", 2007, 2032),
    ("PNC Bank Arts Center – Holmdel, NJ, USA", 1993, 2032),
    ("Wells Fargo Center – Philadelphia, PA, USA", 1996, 2032),
    ("The Spectrum – Philadelphia, PA, USA", 1993, 2009),
    ("TD Garden – Boston, MA, USA", 1995, 2032),
    ("Xfinity Center – Mansfield, MA, USA", 1993, 2032),
    ("DCU Center – Worcester, MA, USA", 1993, 2032),
    ("Giant Center – Hershey, PA, USA", 2002, 2032),
    ("Mohegan Sun Arena – Uncasville, CT, USA", 2001, 2032),
    ("Capital One Arena – Washington, DC, USA", 1997, 2032),
    ("CFG Bank Arena – Baltimore, MD, USA", 1993, 2032),
    ("Hampton Coliseum – Hampton, VA, USA", 1993, 2032),
    ("Norfolk Scope – Norfolk, VA, USA", 1993, 2032),
    ("Merriweather Post Pavilion – Columbia, MD, USA", 1993, 2032),
    ("BankNH Pavilion – Gilford, NH, USA", 1996, 2032),
    ("Bryce Jordan Center – University Park, PA, USA", 1996, 2032),
    ("PPL Center – Allentown, PA, USA", 2014, 2032),
    ("PNC Music Pavilion – Charlotte, NC, USA", 1993, 2032),
    ("Coastal Credit Union Music Park – Raleigh, NC, USA", 1993, 2032),
    ("Lenovo Center – Raleigh, NC, USA", 1999, 2032),
    ("Greensboro Coliseum – Greensboro, NC, USA", 1993, 2032),
    ("Bojangles Coliseum – Charlotte, NC, USA", 1993, 2032),
    ("Colonial Life Arena – Columbia, SC, USA", 2002, 2032),
    ("Bon Secours Wellness Arena – Greenville, SC, USA", 1998, 2032),
    ("VyStar Veterans Memorial Arena – Jacksonville, FL, USA", 2003, 2032),
    ("Ameris Bank Amphitheatre – Alpharetta, GA, USA", 2008, 2032),
    ("State Farm Arena – Atlanta, GA, USA", 1999, 2032),
    ("Lakewood Amphitheatre – Atlanta, GA, USA", 1993, 2032),
    ("Legacy Arena – Birmingham, AL, USA", 1993, 2032),
    ("Oak Mountain Amphitheatre – Pelham, AL, USA", 1993, 2032),
    ("Mississippi Coast Coliseum – Biloxi, MS, USA", 1993, 2032),
    ("Smoothie King Center – New Orleans, LA, USA", 1999, 2032),
    ("FedExForum – Memphis, TN, USA", 2004, 2032),
    ("Bridgestone Arena – Nashville, TN, USA", 1996, 2032),
    ("Thompson–Boling Arena – Knoxville, TN, USA", 1993, 2032),
    ("Cajundome – Lafayette, LA, USA", 1993, 2032),
    ("BOK Center – Tulsa, OK, USA", 2008, 2032),
    ("United Center – Chicago, IL, USA", 1994, 2032),
    ("Allstate Arena – Rosemont, IL, USA", 1993, 2032),
    ("Fiserv Forum – Milwaukee, WI, USA", 2018, 2032),
    ("Xcel Energy Center – St. Paul, MN, USA", 2000, 2032),
    ("Target Center – Minneapolis, MN, USA", 1993, 2032),
    ("Pinnacle Bank Arena – Lincoln, NE, USA", 2013, 2032),
    ("T-Mobile Center – Kansas City, MO, USA", 2007, 2032),
    ("Hollywood Casino Amphitheatre – Maryland Heights, MO, USA", 1993, 2032),
    ("Enterprise Center – St. Louis, MO, USA", 1994, 2032),
    ("Gainbridge Fieldhouse – Indianapolis, IN, USA", 1999, 2032),
    ("Little Caesars Arena – Detroit, MI, USA", 2017, 2032),
    ("Pine Knob Music Theatre – Clarkston, MI, USA", 1993, 2032),
    ("Rocket Arena – Cleveland, OH, USA", 1994, 2032),
    ("Blossom Music Center – Cuyahoga Falls, OH, USA", 1993, 2032),
    ("Riverbend Music Center – Cincinnati, OH, USA", 1993, 2032),
    ("Heritage Bank Center – Cincinnati, OH, USA", 1993, 2032),
    ("Nutter Center – Dayton, OH, USA", 1993, 2032),
    ("KeyBank Center – Buffalo, NY, USA", 1996, 2032),
    ("Buffalo Memorial Auditorium – Buffalo, NY, USA", 1993, 1996),
    ("Richfield Coliseum – Richfield, OH, USA", 1993, 1994),
    ("Capital Centre – Landover, MD, USA", 1993, 2002),
    ("Reunion Arena – Dallas, TX, USA", 1993, 2008),
    ("The Omni – Atlanta, GA, USA", 1993, 1997),
    ("Maple Leaf Gardens – Toronto, ON, Canada", 1993, 1999),
    ("Montreal Forum – Montreal, QC, Canada", 1993, 1996),
    ("Colisée de Québec – Québec City, QC, Canada", 1993, 2015),
    ("Winnipeg Arena – Winnipeg, MB, Canada", 1993, 2004),
    ("Northlands Coliseum – Edmonton, AB, Canada", 1993, 2018),
    ("Budweiser Stage – Toronto, ON, Canada", 1995, 2027),
    ("Scotiabank Arena – Toronto, ON, Canada", 1999, 2032),
    ("Canadian Tire Centre – Ottawa, ON, Canada", 1996, 2032),
    ("Bell Centre – Montreal, QC, Canada", 1996, 2032),
    ("Centre Vidéotron – Québec City, QC, Canada", 2015, 2032),
    ("Budweiser Gardens – London, ON, Canada", 2002, 2032),
    ("Canada Life Centre – Winnipeg, MB, Canada", 2004, 2032),
    ("Rogers Arena – Vancouver, BC, Canada", 1995, 2032),
    ("Pacific Coliseum – Vancouver, BC, Canada", 1993, 2032),
    ("Scotiabank Saddledome – Calgary, AB, Canada", 1993, 2027),
    ("Rogers Place – Edmonton, AB, Canada", 2016, 2032),
    ("SaskTel Centre – Saskatoon, SK, Canada", 1993, 2032),
    ("Ball Arena – Denver, CO, USA", 1999, 2032),
    ("Fiddler’s Green Amphitheatre – Greenwood Village, CO, USA", 1993, 2032),
    ("Red Rocks Amphitheatre – Morrison, CO, USA", 1993, 2032),
    ("Delta Center – Salt Lake City, UT, USA", 1993, 2032),
    ("Utah First Credit Union Amphitheatre – West Valley City, UT, USA", 1993, 2032),
    ("Tacoma Dome – Tacoma, WA, USA", 1993, 2032),
    ("Climate Pledge Arena – Seattle, WA, USA", 1993, 2032),
    ("Moda Center – Portland, OR, USA", 1995, 2032),
    ("Oakland Arena – Oakland, CA, USA", 1993, 2032),
    ("Chase Center – San Francisco, CA, USA", 2019, 2032),
    ("Shoreline Amphitheatre – Mountain View, CA, USA", 1993, 2032),
    ("Golden 1 Center – Sacramento, CA, USA", 2016, 2032),
    ("Cow Palace – Daly City, CA, USA", 1993, 2032),
    ("Kia Forum – Inglewood, CA, USA", 1993, 2032),
    ("Hollywood Bowl – Los Angeles, CA, USA", 1993, 2032),
    ("Pechanga Arena – San Diego, CA, USA", 1993, 2032),
    ("North Island Credit Union Amphitheatre – Chula Vista, CA, USA", 1998, 2032),
    ("PHX Arena – Phoenix, AZ, USA", 1993, 2032),
    ("Desert Diamond Arena – Glendale, AZ, USA", 2003, 2032),
    ("T-Mobile Arena – Las Vegas, NV, USA", 2016, 2032),
    ("Rose Bowl – Pasadena, CA, USA", 1995, 2032),
    ("Los Angeles Memorial Coliseum – Los Angeles, CA, USA", 1995, 2032),
    ("Dodger Stadium – Los Angeles, CA, USA", 1995, 2032),
    ("Oakland Coliseum – Oakland, CA, USA", 1995, 2032),
    ("Oracle Park – San Francisco, CA, USA", 2000, 2032),
    ("Levi’s Stadium – Santa Clara, CA, USA", 2014, 2032),
    ("SoFi Stadium – Inglewood, CA, USA", 2020, 2032),
    ("San Diego Stadium – San Diego, CA, USA", 1995, 2020),
    ("Stanford Stadium – Stanford, CA, USA", 1995, 2032),
    ("California Memorial Stadium – Berkeley, CA, USA", 1995, 2032),
    ("Allegiant Stadium – Las Vegas, NV, USA", 2020, 2032),
    ("Sam Boyd Stadium – Whitney, NV, USA", 1995, 2020),
    ("State Farm Stadium – Glendale, AZ, USA", 2006, 2032),
    ("Sun Devil Stadium – Tempe, AZ, USA", 1995, 2032),
    ("Empower Field at Mile High – Denver, CO, USA", 2001, 2032),
    ("Folsom Field – Boulder, CO, USA", 1995, 2032),
    ("Lumen Field – Seattle, WA, USA", 2002, 2032),
    ("Husky Stadium – Seattle, WA, USA", 1995, 2032),
    ("Seattle Kingdome – Seattle, WA, USA", 1995, 2000),
    ("BC Place – Vancouver, BC, Canada", 1995, 2032),
    ("Rogers Centre – Toronto, ON, Canada", 1995, 2032),
    ("Olympic Stadium – Montreal, QC, Canada", 1995, 2032),
    ("Commonwealth Stadium – Edmonton, AB, Canada", 1995, 2032),
    ("Exhibition Stadium – Toronto, ON, Canada", 1995, 1996),
    ("MetLife Stadium – East Rutherford, NJ, USA", 2010, 2032),
    ("Giants Stadium – East Rutherford, NJ, USA", 1995, 2010),
    ("Yankee Stadium – Bronx, NY, USA", 2009, 2032),
    ("Shea Stadium – Queens, NY, USA", 1995, 2008),
    ("Fenway Park – Boston, MA, USA", 1995, 2032),
    ("RFK Stadium – Washington, DC, USA", 1995, 2019),
    ("Soldier Field – Chicago, IL, USA", 1995, 2032),
    ("Wrigley Field – Chicago, IL, USA", 1995, 2032),
    ("Cleveland Municipal Stadium – Cleveland, OH, USA", 1995, 1995),
    ("Three Rivers Stadium – Pittsburgh, PA, USA", 1995, 2000),
    ("Ford Field – Detroit, MI, USA", 2002, 2032),
    ("Pontiac Silverdome – Pontiac, MI, USA", 1995, 2013),
    ("Hubert H. Humphrey Metrodome – Minneapolis, MN, USA", 1995, 2013),
    ("U.S. Bank Stadium – Minneapolis, MN, USA", 2016, 2032),
    ("Veterans Stadium – Philadelphia, PA, USA", 1995, 2003),
    ("Cotton Bowl – Dallas, TX, USA", 1995, 2032),
    ("AT&T Stadium – Arlington, TX, USA", 2009, 2032),
    ("NRG Stadium – Houston, TX, USA", 2002, 2032),
    ("Astrodome – Houston, TX, USA", 1995, 2008),
    ("Alamodome – San Antonio, TX, USA", 1995, 2032),
    ("Superdome – New Orleans, LA, USA", 1995, 2032),
    ("Camping World Stadium – Orlando, FL, USA", 1995, 2032),
    ("Hard Rock Stadium – Miami Gardens, FL, USA", 1995, 2032),
    ("Orange Bowl – Miami, FL, USA", 1995, 2008),
    ("Mercedes-Benz Stadium – Atlanta, GA, USA", 2017, 2032),
    ("New York, NY, USA", 1992, 2032),
    ("Los Angeles, CA, USA", 1992, 2032),
    ("Chicago, IL, USA", 1992, 2032),
    ("Dallas, TX, USA", 1992, 2032),
    ("Houston, TX, USA", 1992, 2032),
    ("Atlanta, GA, USA", 1992, 2032),
    ("Washington, DC, USA", 1992, 2032),
    ("Miami, FL, USA", 1992, 2032),
    ("Philadelphia, PA, USA", 1992, 2032),
    ("Phoenix, AZ, USA", 1992, 2032),
    ("Boston, MA, USA", 1992, 2032),
    ("Riverside, CA, USA", 1992, 2032),
    ("San Francisco, CA, USA", 1992, 2032),
    ("Detroit, MI, USA", 1992, 2032),
    ("Seattle, WA, USA", 1992, 2032),
    ("Minneapolis, MN, USA", 1992, 2032),
    ("Tampa, FL, USA", 1992, 2032),
    ("San Diego, CA, USA", 1992, 2032),
    ("Denver, CO, USA", 1992, 2032),
    ("Orlando, FL, USA", 1992, 2032),
    ("Charlotte, NC, USA", 1992, 2032),
    ("Baltimore, MD, USA", 1992, 2032),
    ("St. Louis, MO, USA", 1992, 2032),
    ("San Antonio, TX, USA", 1992, 2032),
    ("Austin, TX, USA", 1992, 2032),
    ("Portland, OR, USA", 1992, 2032),
    ("Sacramento, CA, USA", 1992, 2032),
    ("Pittsburgh, PA, USA", 1992, 2032),
    ("Las Vegas, NV, USA", 1992, 2032),
    ("Springfield, OH, USA", 1992, 2032),
    ("Dayton, OH, USA", 1992, 2032),
    ("Cincinnati, OH, USA", 1992, 2032),
    ("Vandalia, OH, USA", 1992, 2032),
    ("Over-the-Rhine, OH, USA", 1999, 2032),
    ("Kansas City, MO, USA", 1992, 2032),
    ("Columbus, OH, USA", 1992, 2032),
    ("Indianapolis, IN, USA", 1992, 2032),
    ("Nashville, TN, USA", 1992, 2032),
    ("Cleveland, OH, USA", 1992, 2032),
    ("San Jose, CA, USA", 1992, 2032),
    ("Virginia Beach, VA, USA", 1992, 2032),
    ("Jacksonville, FL, USA", 1992, 2032),
    ("Providence, RI, USA", 1992, 2032),
    ("Raleigh, NC, USA", 1992, 2032),
    ("Milwaukee, WI, USA", 1992, 2032),
    ("Oklahoma City, OK, USA", 1992, 2032),
    ("Louisville, KY, USA", 1992, 2032),
    ("Richmond, VA, USA", 1992, 2032),
    ("Memphis, TN, USA", 1992, 2032),
    ("Salt Lake City, UT, USA", 1992, 2032),
    ("Fresno, CA, USA", 1992, 2032),
    ("Birmingham, AL, USA", 1992, 2032),
    ("Grand Rapids, MI, USA", 1992, 2032),
    ("Hartford, CT, USA", 1992, 2032),
    ("Buffalo, NY, USA", 1992, 2032),
    ("Tucson, AZ, USA", 1992, 2032),
    ("Tulsa, OK, USA", 1992, 2032),
    ("Rochester, NY, USA", 1992, 2032),
    ("Ann Arbor, MI, USA", 1989, 1992),
    ("Athens, OH, USA", 1989, 1992),
    ("Bellefontaine, OH, USA", 1989, 1992),
    ("Celina, OH, USA", 1989, 1992),
    ("Chillicothe, OH, USA", 1989, 1992),
    ("Fairfield, OH, USA", 1989, 1992),
    ("Findlay, OH, USA", 1989, 1992),
    ("Florence, KY, USA", 1989, 1992),
    ("Hamilton, OH, USA", 1989, 1992),
    ("Kent, OH, USA", 1989, 1992),
    ("Lima, OH, USA", 1989, 1992),
    ("Mason, OH, USA", 1989, 1992),
    ("Marysville, OH, USA", 1989, 1992),
    ("Middletown, OH, USA", 1989, 1992),
    ("Montgomery, OH, USA", 1989, 1992),
    ("New Carlisle, OH, USA", 1989, 1992),
    ("Piqua, OH, USA", 1989, 1992),
    ("Port Clinton, OH, USA", 1989, 1992),
    ("Powell, OH, USA", 1989, 1992),
    ("Richmond, IN, USA", 1989, 1992),
    ("Sandusky, OH, USA", 1989, 1992),
    ("Sidney, OH, USA", 1989, 1992),
    ("Tipp City, OH, USA", 1989, 1992),
    ("Toledo, OH, USA", 1989, 1992),
    ("Troy, OH, USA", 1989, 1992),
    ("Wapakoneta, OH, USA", 1989, 1992),
    ("Washington Court House, OH, USA", 1989, 1992),
    ("Wheeling, WV, USA", 1989, 1992),
    ("Wooster, OH, USA", 1989, 1992),
    ("Zanesville, OH, USA", 1989, 1992),
]

CENTRAL_CONFLICTS = [
    "A fragile alliance fractures under paranoia and yelling",
    "After too much drinking, a revelation starts rewriting old betrayals",
    "An emerging technology promises salvation but erodes the band's identity",
    "An oath made years ago now demands an impossible sacrifice",
    "art and business collide when honesty could hurt innocent people",
    "Island Records and Cremeans bicker over resources while a third force profits",
    "the protagonist agrees to disagree with the secondary character after intense debate",
    "the protagonist and secondary character, after long argument, cannot abide each other and opt to go separate ways",
    "the protagonist attempts a compromise with the rest of the band to achieve a collective goal",
    "the protagonist comes to a compromise with the secondary character",
    "the protagonist comes to embrace the secondary character's perspective, so they are on the same side",
    "the protagonist defeats the secondary character physically, intellectually, or emotionally",
    "the protagonist enjoys learning how to use the new music industry technology of the day",
    "the protagonist is angry about not being invited to a meeting that the secondary character led concerning band business",
    "the protagonist is bent on overcoming the latest music industry technology with human heart or intellect",
    "the protagonist is bitter by being defeated by music industry technology espoused by the secondary character",
    "the protagonist is defeated by the secondary character physically, intellectually, or emotionally",
    "the protagonist is forced into submission or defeated by the band, and for good reason",
    "the protagonist is persuaded by rest of the band to give up a bad habit",
    "the protagonist is set about convincing society that it is wrong on a key issue",
    "The protagonist must choose between justice and loyalty",
    "the protagonist struggles with a sense of self and purpose.",
    "the protagonist struggles with accepting or avoiding personal responsibilities.",
    "the protagonist struggles with acting for the greater good versus pursuing personal gain.",
    "the protagonist struggles with acting out of desperation versus waiting for the right time.",
    "the protagonist struggles with acts of kindness versus self-centeredness.",
    "the protagonist struggles with assertiveness dealing with their peers in the band",
    "the protagonist struggles with avoiding reality or facing it.",
    "the protagonist struggles with balancing conflicting desires or goals.",
    "the protagonist struggles with balancing ego and pride with humility.",
    "the protagonist struggles with balancing emotional connections with detachment.",
    "the protagonist struggles with balancing optimism with a realistic perspective.",
    "the protagonist struggles with balancing personal happiness with achieving success.",
    "the protagonist struggles with balancing self-interest with concern for others.",
    "the protagonist struggles with battling addiction or seeking rehabilitation.",
    "the protagonist struggles with becoming someone undesirable vs. becoming who they want to be",
    "the protagonist struggles with becoming unfit to do what is necessary vs. gaining the power and wherewithal to complete the task",
    "the protagonist struggles with being defensive or allowing oneself to be vulnerable.",
    "the protagonist struggles with believing in oneself versus feeling inadequate.",
    "the protagonist struggles with building trust or harboring suspicion.",
    "the protagonist struggles with choosing between love and responsibilities.",
    "the protagonist struggles with choosing ethical actions over expedient ones.",
    "the protagonist struggles with choosing one's safety or sacrificing for others.",
    "the protagonist struggles with choosing to forgive or holding onto resentment.",
    "the protagonist struggles with coming to terms with a painful reality about one's self vs. fully accepting one's self",
    "the protagonist struggles with coming to terms with inevitable changes.",
    "the protagonist struggles with coming to terms with one's own mortality.",
    "the protagonist struggles with confidence, comparing themselves negatively with their industry peers",
    "the protagonist struggles with conflicting wants, as the eternal battle between Art and Profit causes them sleepless nights",
    "the protagonist struggles with connecting with others or becoming emotionally detached.",
    "the protagonist struggles with conquering one's fear or succumbing to it.",
    "the protagonist struggles with contemplating the meaning of life and existence.",
    "the protagonist struggles with controlling anger and its destructive potential.",
    "the protagonist struggles with coping with loss and finding a way to move forward.",
    "the protagonist struggles with coping with love that is not reciprocated.",
    "the protagonist struggles with coping with the fear of being abandoned by loved ones.",
    "the protagonist struggles with coping with the process of aging and the knowledge of mortality.",
    "the protagonist struggles with costs planning for their next big creative idea",
    "the protagonist struggles with creativity, or a better, healthier psychological life",
    "the protagonist struggles with dealing with the consequences of infidelity.",
    "the protagonist struggles with dealing with the fear of changes in one's life.",
    "the protagonist struggles with dealing with the fear of what lies ahead.",
    "the protagonist struggles with deciding whether to tell the truth or maintain a lie.",
    "the protagonist struggles with determination in the face of adversity.",
    "the protagonist struggles with discovering and tapping into one's inner strength.",
    "the protagonist struggles with doubt and faith.",
    "the protagonist struggles with doubt observing their friends in the band",
    "the protagonist struggles with duty vs. personal happiness",
    "the protagonist struggles with dwelling on past regrets or finding acceptance.",
    "the protagonist struggles with embracing individuality versus conforming to societal norms.",
    "the protagonist struggles with facing the fear of rejection in personal relationships.",
    "the protagonist struggles with feeling like a fraud despite success.",
    "the protagonist struggles with having to live with painful regrets vs. having the peace of overcoming",
    "the protagonist struggles with holding onto hope in dire situations.",
    "the protagonist struggles with holding onto the past versus embracing change.",
    "the protagonist struggles with how one's changing nature with fame affects others around the character negatively or positively",
    "the protagonist struggles with letting go of material attachments.",
    "the protagonist struggles with letting go of resentment or holding onto it.",
    "the protagonist struggles with listening to one's conscience versus engaging in unethical behavior.",
    "the protagonist struggles with loneliness or seeking meaningful connections.",
    "the protagonist struggles with loss of identity or sense of self vs. clearer sense of identity or a better sense of self, because the band is a large, found family",
    "the protagonist struggles with loss of power (over self) vs. gaining power (fame and fortune that accompanies stardom)",
    "the protagonist struggles with maintaining a facade versus being genuine.",
    "the protagonist struggles with maintaining a positive outlook or succumbing to negativity.",
    "the protagonist struggles with maintaining one's integrity or succumbing to corruption.",
    "the protagonist struggles with making logical decisions versus acting irrationally.",
    "the protagonist struggles with managing power and its impact on others.",
    "the protagonist struggles with meeting or defying the expectations of parents.",
    "the protagonist struggles with meeting the expectations of others or following one's path.",
    "the protagonist struggles with morality vs. Desire",
    "the protagonist struggles with navigating conflicts related to cultural identity.",
    "the protagonist struggles with obsessive behavior or finding equilibrium.",
    "the protagonist struggles with opening up to others or building walls.",
    "the protagonist struggles with overcoming arrogance or embracing humility.",
    "the protagonist struggles with overcoming envy and finding contentment.",
    "the protagonist struggles with overcoming fear to do what's necessary.",
    "the protagonist struggles with overcoming feelings of inadequacy.",
    "the protagonist struggles with overcoming feelings of insecurity.",
    "the protagonist struggles with overcoming hesitation to take decisive action.",
    "the protagonist struggles with overcoming personal prejudices and biases.",
    "the protagonist struggles with overcoming the fear of commitment in relationships.",
    "the protagonist struggles with overcoming the fear of failing.",
    "the protagonist struggles with passing judgment on others versus showing empathy.",
    "the protagonist struggles with personal fears, doubts, or inner demons.",
    "the protagonist struggles with pursuing competition or fostering cooperation.",
    "the protagonist struggles with questioning authority figures or blindly following them.",
    "the protagonist struggles with refusing to accept a harsh truth or facing it head-on.",
    "the protagonist struggles with resisting authority or adhering to societal norms.",
    "the protagonist struggles with resisting change or rejecting change",
    "the protagonist struggles with resisting impulsive decisions or actions.",
    "the protagonist struggles with resisting temptations or giving in to them.",
    "the protagonist struggles with seeking a fulfilling life versus feeling empty.",
    "the protagonist struggles with seeking revenge versus letting go of anger.",
    "the protagonist struggles with seeking to atone for past mistakes.",
    "the protagonist struggles with seeking vengeance or letting go and forgiving.",
    "the protagonist struggles with showing kindness and empathy versus indifference.",
    "the protagonist struggles with striving for perfection versus accepting imperfections.",
    "the protagonist struggles with taking control of one's life versus feeling like a victim.",
    "the protagonist struggles with the drive for success conflicting with the desire for a simple life.",
    "the protagonist struggles with the fear of being rejected versus the desire to be authentic.",
    "the protagonist struggles with the need for self-identity versus fitting in.",
    "the protagonist struggles with the pursuit of wealth and possessions versus simplicity.",
    "the protagonist struggles with trust issues due to past experiences.",
    "the protagonist struggles with upholding one's moral principles in challenging situations.",
    "the protagonist struggles with wrestling with events or decisions from the past.",
    "the protagonist struggles with wrestling with feelings of guilt or innocence.",
    "the protagonist tries educating the rest of the band on a better way forward",
    "the protagonist tries siding with society, as maybe they are being overly provocative",
    "the protagonist tries to persuade the band to allow the character to pursue their singular musical goal",
    "the protagonist tries to show off their particular musical genius and asks the secondary character's advice",
    "the protagonist wants the secondary character thrown off the tour bus for being too risky and an asshole",
    "There's potentially a lot of money to be made, but only if the wrong person makes it first.",
]

INCITING_PRESSURES = [
    "a concert promoter seems pretty damn fair",
    "A deranged fan attempts murder",
    "A loved one or friend has been unfaithful",
    "A loved one/friend dies and the protagonist is extremely upset",
    "a process server serves legal papers",
    "Arrested by frame-up for weed possession",
    "Arrested falsely",
    "Arrested for minor infraction",
    "Bad health news troubles the protagonist",
    "Be blackmailed (possibly forced to do something)",
    "Become lost",
    "Bill boasts how weed can cure all ails",
    "Bill wants a new mic",
    "buys a fancy new car",
    "celebrates a successful write-up in a local alt-weekly",
    "cell phone service sucks",
    "Change location/base of operations because of improved economic status",
    "Come across a crime in progress",
    "Cremeans threatens the protagonist by deducting damages from royalties",
    "demands privacy on the bus to masturbate/have sex",
    "Disaster damages their dwelling or base of operations",
    "Earnest fan explains how they've been positively influenced",
    "Explore interesting location",
    "Find a body (or other evidence of a crime)",
    "Find a valuable bootleg",
    "Find forbidden object",
    "gets a ticket for a wild speeding violation",
    "gets high after a show",
    "Gilley gives a ridiculous, over the top interview",
    "Gilley has the most ridiculous outfit for clubbing",
    "Help a stranger with a problem",
    "Injury or sickness waylays a member of the band",
    "Install new technology",
    "Investigate local legend or historical site",
    "Jeff decides quite abrasively that the protagonist is wrong",
    "Jeremy and Jim argue about great drummers",
    "Jeremy wants a new pedal",
    "Kathy may have committed blasphemy again",
    "Kathy wants the guys to care more about fashion",
    "Kathy's volcanic temper explodes",
    "Mechanical breakdown of their favorite kit",
    "Meet benevolent stranger",
    "Meet cute woman who is sexually adventurous towards the protagonist",
    "Mistaken identity with another celeb",
    "Must find expert to fix serious problem",
    "Natural disaster impacts their location",
    "Object of a challenge",
    "object of desire",
    "object of ridicule",
    "Prospective new sponsor seems to be an asshole",
    "Rescue a pet",
    "Sarah has a great idea",
    "Start a new lyrics writing assignment",
    "Stumble on dangerous knowledge",
    "Terminated from job/assignment",
    "the character's GP is pissed at the protagonist",
    "the characters determine the promoter is an asshole",
    "The characters meet an old friend",
    "the characters sip alcohol and debate the nature of truth, art, and dinner",
    "the characters wish they were somewhere more peaceful like a hockey game",
    "the protagonist antagonizes Kendall",
    "The protagonist becomes separated from their lover",
    "The protagonist finds out they are being stalked",
    "The protagonist gets a rave local media review.",
    "the protagonist has a runny nose and sniffles",
    "the protagonist is unable to climax",
    "the protagonist was interrupted while having sex",
    "the protagonist's groupie is annoying",
    "Unexplained incident",
]

ENDING_TYPES = [
    "ambiguous",
    "bittersweet",
    "celebration",
    "cutting, sharp, and penetrating",
    "despair",
    "drunken denial",
    "emotionally drained",
    "explosive anger",
    "happy",
    "hopeful",
    "horror",
    "lusty",
    "melancholy and full of ennui",
    "open-ended",
    "pleased and praised",
    "pyrrhic victory",
    "redemptive",
    "rousing success",
    "they go their separate ways",
    "time to party",
    "tragic",
    "twist ending",
    "well-executed",
    "wrecked",
]

STYLE_GUIDANCE = [
    "backstage realism with gritty industry detail. Studios, promoters, contracts, tour buses, and the machinery of music.",
    "cinematic hybrid screenplay-prose with strong scene geometry. Sacred slug lines, visual blocking, tactile action lines, and interior narration woven together like a film script that refuses to behave.",
    "cinematic third-person with escalating tension",
    "cinematic third-person with escalating tension and sharp visual beats. Scenes unfold like camera setups, each paragraph tightening the screws.",
    "darkly comic tone balancing dread and absurdity",
    "darkly comic tone balancing dread, absurdity, and gallows humor. Characters joke because the alternative is screaming.",
    "documentary-style narrative with archival texture and historical framing. Reads like a recovered document, interview, or historian’s reconstruction of events.",
    "elegant but explicit sensuality with emotional consequence. Sex scenes that are specific, choreographed, and narratively meaningful.",
    "elegiac tone with grief treated as ritual and memory. Loss slows time and turns ordinary rooms into sacred spaces.",
    "ensemble dialogue-driven scenes with quick humor and emotional crossfire. Multiple characters in motion, verbal energy carrying the scene.",
    "episodic road-movie storytelling with shifting locations and momentum. Movement drives the structure: airports, highways, hotel rooms, backstage corridors.",
    "intimate confessional voice with emotional honesty and self-interrogation. Characters narrate their own contradictions without mercy.",
    "intimate first-person voice with emotional honesty",
    "lean prose, sharp dialogue, fast pacing",
    "literary style with thematic motifs and callbacks",
    "lyrical but grounded, vivid sensory detail",
    "lyrical realism rooted in physical place and sensory detail. Weather, light, geography, and sound shape the emotional landscape.",
    "melancholy nostalgia with vivid sensory recall. Characters revisit places or events that refuse to stay in the past.",
    "mythic rock-epic tone treating music and performance as cultural history. Band moments are framed like historical turning points.",
    "noir-inflected narration with moral ambiguity",
    "noir-inflected narration with moral ambiguity and institutional tension. Lawyers, reporters, police, managers, and power structures lurk in the shadows.",
    "psychological realism exploring obsession, ego, and emotional fracture. Inner turmoil becomes the engine of the story.",
    "raw bodily realism portraying desire, fatigue, intoxication, and vulnerability. The body is treated honestly, without euphemism.",
    "reflective literary tone with thematic motifs and callbacks. Images and ideas echo across scenes like musical refrains.",
    "sharp, lean prose emphasizing action and momentum. Minimal ornamentation, fast pacing, muscular verbs.",
    "spectacle-driven storytelling with public performance and media attention. Concerts, TV appearances, interviews, and large public moments.",
    "warm, bruised character-driven storytelling with quiet emotional stakes. Relationships matter more than plot, but the emotional pressure keeps rising.",
    "warm, character-driven storytelling with quiet stakes",
]

WORD_COUNT_TARGETS = [1500, 2000, 2400, 3000, 3600, 4000, 5000]

WRITING_PREAMBLE = (
    "Interpret the YAML and write a deliciously wild short story, based on the material. "
    "You may indulge yourself in every regard. Use the canon, and writing style guidelines. "
    "Before writing the final story, use your writing style-book guidelines: "
    "1. Scene headers use slug format. "
    "2. Dialogue appears only in CHARACTER NAME blocks. "
    "3. No dialogue appears inside prose paragraphs. "
    "4. Character names in dialogue blocks are ALL CAPS."
)

SEXUAL_CONTENT_OPTIONS = [
    "none",
    "if_creatively_merited",
    "implied",
    "required",
    "central",
]

SEXUAL_CONTENT_WEIGHTS = [0.60, 0.10, 0.10, 0.10, 0.10]

ORDERED_KEYS = [
    "title",
    "protagonist",
    "secondary_character",
    "time_period",
    "setting",
    "central_conflict",
    "inciting_pressure",
    "ending_type",
    "style_guidance",
    "sexual_content_level",
    "word_count_target",
]

TITLE_TOKEN_PATTERN = re.compile(r"@(?P<key>protagonist|setting|time_period)\b")


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def escape_markdown_heading_text(value: str) -> str:
    """Escape Markdown-significant characters for safe heading rendering."""
    return re.sub(r"([\\\\`*_{}\[\]()#+\-.!])", r"\\\1", value)


def random_date_in_range(
    rng: random.Random | secrets.SystemRandom, start: date, end: date
) -> date:
    """Return a random date between start and end (inclusive)."""
    day_span = (end - start).days
    return start + timedelta(days=rng.randint(0, day_span))


def available_characters(selected_date: date) -> list[str]:
    """Return characters available for the selected date's year."""
    year = selected_date.year
    return [
        name
        for name, start_year, end_year in CHARACTER_AVAILABILITY
        if start_year <= year <= end_year
    ]


def available_settings(selected_date: date) -> list[str]:
    """Return settings available for the selected date's year."""
    year = selected_date.year
    return [
        setting
        for setting, start_year, end_year in SETTING_AVAILABILITY
        if start_year <= year <= end_year
    ]


def weighted_choice(
    rng: random.Random | secrets.SystemRandom,
    options: list[str],
    weights: list[float],
) -> str:
    """Pick one option using relative weights."""
    if not options:
        raise ValueError("options must not be empty")
    if len(options) != len(weights):
        raise ValueError("options and weights must be the same length")
    if not weights:
        raise ValueError("weights must not be empty")

    for index, weight in enumerate(weights):
        if isinstance(weight, bool) or not isinstance(weight, (int, float)):
            raise TypeError(f"weight at index {index} must be a real number")
        if not math.isfinite(weight):
            raise ValueError(f"weight at index {index} must be finite")
        if weight < 0:
            raise ValueError(f"weight at index {index} must be non-negative")

    total = sum(weights)
    if total <= 0:
        raise ValueError("at least one weight must be greater than zero")

    threshold = rng.random() * total
    cumulative = 0.0

    for option, weight in zip(options, weights):
        cumulative += weight
        if threshold <= cumulative:
            return option

    return options[-1]


def render_title(
    template: str, *, protagonist: str, setting: str, time_period: str
) -> str:
    """Render @token placeholders in title templates."""
    values = {
        "protagonist": protagonist,
        "setting": setting,
        "time_period": time_period,
    }
    return TITLE_TOKEN_PATTERN.sub(lambda match: values[match.group("key")], template)


def pick_story_fields(rng: random.Random | secrets.SystemRandom) -> dict[str, str | int]:
    # Determine date first so future character-availability rules can depend on it.
    selected_date = random_date_in_range(rng, DATE_START, DATE_END)
    time_period = selected_date.isoformat()

    characters_for_date = available_characters(selected_date)
    if len(characters_for_date) < 2:
        raise ValueError(
            f"Need at least two available characters for year {selected_date.year}."
        )
    settings_for_date = available_settings(selected_date)
    if not settings_for_date:
        raise ValueError(
            f"No settings are available for year {selected_date.year}. "
            "Check SETTING_AVAILABILITY."
        )

    protagonist = rng.choice(characters_for_date)
    eligible_secondary = [name for name in characters_for_date if name != protagonist]
    secondary_character = rng.choice(eligible_secondary)
    setting = rng.choice(settings_for_date)
    title_template = rng.choice(TITLES)

    return {
        "title": render_title(
            title_template,
            protagonist=protagonist,
            setting=setting,
            time_period=time_period,
        ),
        "protagonist": protagonist,
        "secondary_character": secondary_character,
        "time_period": time_period,
        "setting": setting,
        "central_conflict": rng.choice(CENTRAL_CONFLICTS),
        "inciting_pressure": rng.choice(INCITING_PRESSURES),
        "ending_type": rng.choice(ENDING_TYPES),
        "style_guidance": rng.choice(STYLE_GUIDANCE),
        "sexual_content_level": weighted_choice(
            rng, SEXUAL_CONTENT_OPTIONS, SEXUAL_CONTENT_WEIGHTS
        ),
        "word_count_target": rng.choice(WORD_COUNT_TARGETS),
    }


def to_markdown(fields: dict[str, str | int]) -> str:
    ordered_fields = {key: fields[key] for key in ORDERED_KEYS}
    yaml_text = yaml.safe_dump(
        ordered_fields,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    ).strip()

    body = [
        "---",
        yaml_text,
        "---",
        "",
        WRITING_PREAMBLE,
        "",
        f"# {escape_markdown_heading_text(str(fields['title']))}",
        "",
        "## Story Draft",
        "",
        (
            f"*Write a story of approximately {fields['word_count_target']} words "
            "using the YAML brief above.*"
        ),
        "",
    ]
    return "\n".join(body)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a random story brief Markdown file with YAML front matter."
        )
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default="8. Story Seeds",
        help="Directory where the markdown file will be written.",
    )
    parser.add_argument(
        "--filename", help="Optional explicit filename for the markdown file."
    )
    parser.add_argument(
        "--seed", type=int, help="Optional random seed for reproducible output."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow overwriting an existing output file.",
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="Print the generated markdown to the terminal and do not write a file.",
    )
    args = parser.parse_args()

    # Use cryptographically strong randomness by default.
    # If --seed is supplied, keep deterministic behavior for reproducible tests.
    rng: random.Random | secrets.SystemRandom
    if args.seed is None:
        rng = secrets.SystemRandom()
    else:
        rng = random.Random(args.seed)
    fields = pick_story_fields(rng)
    markdown = to_markdown(fields)

    if args.print_only:
        print(markdown)
        return

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.filename:
        filename = Path(args.filename).name
    else:
        today_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{today_str} {slugify(str(fields['title']))}.md"

    output_path = output_dir / filename
    if output_path.exists() and not args.force:
        raise SystemExit(
            f"Refusing to overwrite existing file: {output_path}. "
            "Use --force to overwrite."
        )

    output_path.write_text(markdown, encoding="utf-8")
    print(f"Generated {output_path}")


if __name__ == "__main__":
    main()

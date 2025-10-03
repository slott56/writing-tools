"""
The 108 human miseries. In alphabetical order.

See https://mrob.com/pub/epist/buddhism.html

Alternative...

{eye, ear, nose, tongue, body, mind} × {gladness, sadness, equanimity} × {household life, renunciation} × {past, future, present} 

"""
import random

miseries="""
abuse; aggression; ambition; anger; arrogance; baseness; blasphemy; 
calculation; callousness; capriciousness (unaccountable changes of mood or
behavior); 
censoriousness (being severely critical of others); conceitedness; contempt;
cruelty; 
cursing; debasement; deceit; deception; delusion; derision; desire for fame; 
dipsomania (alcoholism characterized by intermittent bouts of craving); discord;
disrespect; disrespectfulness; dissatisfaction; dogmatism; dominance; eagerness
for power; 
effrontery (insolent or impertinent behavior); egoism; enviousness; envy;
excessiveness; 
faithlessness; falseness; furtiveness; gambling; 
garrulity (tediously talking about trivial matters); gluttony; greed; greed for
money; 
grudge; hard-heartedness; hatred; haughtiness; high-handedness; hostility;
humiliation; 
hurt; hypocrisy; ignorance; 
imperiousness (assuming power or authority without justification); 
imposture (pretending to be someone else in order to deceive); impudence; 
inattentiveness; indifference; ingratitude; insatiability; insidiousness;
intolerance; 
intransigence (unwilling or refusing to change one's views or to agree about
something); 
irresponsibility; jealousy; know-it-all; lack of comprehension; lecherousness;
lying; 
malignancy; manipulation; masochism; mercilessness; negativity; obsession;
obstinacy; 
obstinacy; oppression; ostentatiousness; pessimism; prejudice; presumption;
pretence; 
pride; prodigality (spending money or using resources freely and recklessly); 
quarrelsomeness; rage; rapacity (being aggressively greedy or grasping);
ridicule; sadism; sarcasm; seducement; self-denial; self-hatred; sexual lust;
shamelessness; stinginess; stubbornness; torment; tyranny; unkindness;
unruliness; unyielding; vanity; vindictiveness; violence; violent temper;
voluptuousness; wrath
"""

# Reassemble a single string, then parse and clean
miseries_list = [item.strip() 
    for item in " ".join(filter(None, miseries.splitlines())).split(';')
]

def miseries(n=5):
    for i in range(n):
        print(random.choice(miseries_list))

if __name__ == "__main__":
    miseries()

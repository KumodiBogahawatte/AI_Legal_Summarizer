from app.services.fundamental_rights_detector import FundamentalRightsDetector
from app.services.constitutional_article_detector import ConstitutionalArticleDetector
import json

text = """Constitution Articles 12, 141, 17, 126, and 140  Rationale for expanding canvas of locus standi.
In their petition they expressly state invoking jurisdiction in terms of Article 140 of the Constitution.
CASA is a company limited by guarantee incorporated under the Companies Act, No. 17 of 1982.
"""

fr = FundamentalRightsDetector(semantic_threshold=0.70)
const = ConstitutionalArticleDetector(semantic_threshold=0.70)

fr_results = fr.detect(text)
const_results = const.detect(text)

print("=== FR Results ===")
print(json.dumps(fr_results, indent=2))
print("\n=== Constitutional Results ===")
print(json.dumps(const_results, indent=2))

"""
uv run initial_prototypes/evaluation.py
"""

from scipy import stats


def normalize(series: list[str]) -> list[int]:
  """
  Normalize 'mm:ss' to # seconds for
  each element in a list
  """ 
  return [
    int(i.split(":")[0]) * 60 + int(i.split(":")[1])
    for i in series
  ]

def anova():

  # A: Baseline
  A = normalize(['04:28', '01:09', '01:20'])
  # B: Multi-add with feedback
  B = normalize(['01:19', '01:38', '00:57'])
  # C: Ungrouped call-response
  C = normalize(['02:31', '01:47', '01:36'])
  # D: Grouped call-response
  D = normalize(['01:07', '01:23', '01:01'])

  

  F, p = stats.f_oneway(A, B, C, D)

  print(f"F={F} p={p}")
  print(f"Null Hypothesis is {"REJECTED" if p<0.05 else "NOT REJECTED"}")


if __name__ == '__main__':
  anova()
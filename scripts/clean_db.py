import sqlite3

conn = sqlite3.connect('resume_ranker.db')
c = conn.cursor()
c.execute("DELETE FROM match_results")
c.execute("DELETE FROM resumes")
c.execute("DELETE FROM job_descriptions")
conn.commit()
print("Cleaned resume_ranker.db successfully! All old records cleared.")
conn.close()

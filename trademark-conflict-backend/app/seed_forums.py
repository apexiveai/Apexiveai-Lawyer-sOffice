from sqlalchemy import select

from app.core import SessionLocal

from app.models.category import Category

CATEGORIES = [

    {

        "name": "Security",

        "slug": "security",

        "description": (

            "Cybersecurity, application security, "

            "identity, privacy, vulnerabilities, "

            "and security engineering."

        ),

    },

    {

        "name": "Data & Cloud",

        "slug": "data-cloud",

        "description": (

            "Cloud computing, databases, data engineering, "

            "DevOps, infrastructure, and distributed systems."

        ),

    },

    {

        "name": "Development",

        "slug": "development",

        "description": (

            "Frontend, backend, full-stack, mobile development, "

            "APIs, programming, and developer tools."

        ),

    },

    {

        "name": "Artificial Intelligence",

        "slug": "artificial-intelligence",

        "description": (

            "AI, machine learning, LLMs, AI agents, "

            "RAG, knowledge systems, and computer vision."

        ),

    },

]

def seed():

    db = SessionLocal()

    try:

        for item in CATEGORIES:

            exists = db.execute(

                select(Category)

                .where(

                    Category.slug == item["slug"]

                )

            ).scalar_one_or_none()

            if exists:

                continue

            db.add(

                Category(

                    name=item["name"],

                    slug=item["slug"],

                    description=item["description"],

                )

            )

        db.commit()

        print("Forum categories seeded successfully.")

    finally:

        db.close()

if __name__ == "__main__":

    seed()
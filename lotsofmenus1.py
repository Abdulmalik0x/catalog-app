from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Categories, Base, CategoryItems, User
import os

os.chdir("D:/Documents/GitHub/Item Catalog App/")

engine = create_engine('sqlite:///itemscategory.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)

# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()


# Create dummy user
newUser = User(name="Robo Barista", email="me@training.com", picture='https://pbs.twimg.com/profile_images/2671170543/18debd694829ed78203a5a36dd364160_400x400.png')
session.add(newUser)
session.commit()

category1 = Categories(name="Politicss")

session.add(category1)
session.commit()

menuItem2 = CategoryItems(title="Veggie Burger", description="Juicy grilled veggie patty with tomato mayo and lettuce",
                    categories=category1)

session.add(menuItem2)
session.commit()

print (session.query(Categories).all())


print ("added menu items!")
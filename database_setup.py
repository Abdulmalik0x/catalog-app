from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy_dao.model import Model
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
import os


os.chdir("D:/Documents/GitHub/Item Catalog App/")

engine = create_engine('sqlite:///itemscategory.db',
                       connect_args={'check_same_thread': False})
Base = declarative_base()


class User(Base):
    """This class is to store to handle users information upon
    logining through the ouath gate"""
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'id': self.id,
            'email': self.email,
            'picture': self.picture
        }


class Categories(Base):
    """
    This class is to handle all the categories
    :id param: auto generated
    :name param: name of the category
    """
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False, unique=True)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'id': self.id,
        }


class CategoryItems(Base):
    """
    This class is to handle all the items associated with categeroies table
    :id param: auto generated
    :title param: name of the item
    :description param: desc about the item
    :categoryId param: to link it with the parent category
    :creatorId param: will be fetched from logged user
    """
    __tablename__ = 'category_Items'

    id = Column(Integer, primary_key=True)
    title = Column(String(80), nullable=False)
    description = Column(String(250))
    categoryId = Column(Integer, ForeignKey('categories.id'))
    creatorId = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)
    categories = relationship(Categories, cascade="all,\
    delete-orphan", single_parent=True)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'categoryId': self.categoryId,
            'creatorId': self.creatorId,
            # 'categoryName': self.categoryName,
        }

""" Instead of creating a schema automatically from
the SQLAlchemy, as what's shown in the previous articles
using Base.metadata.create_all(engine) """
Base.metadata.create_all(engine)

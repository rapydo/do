# -*- coding: utf-8 -*-

"""
Graph DB abstraction from neo4j server.
These are custom models!

VERY IMPORTANT!
Imports and models have to be defined/used AFTER normal Graphdb connection.
"""

from neomodel import ZeroOrMore, OneOrMore

from neomodel.util import NodeClassRegistry

from restapi.connectors.neo4j.types import (
    StringProperty,
    IntegerProperty,
    DateProperty,
    DateTimeProperty,
    JSONProperty,
    ArrayProperty,
    FloatProperty,
    BooleanProperty,
    AliasProperty,
    IdentifiedNode,
    StructuredRel,
    TimestampedNode,
    RelationshipTo,
    RelationshipFrom,
    # UniqueIdProperty
)
from restapi.models.neo4j import User as UserBase

# from restapi.utilities.logs import log


registry = NodeClassRegistry()
base_user = frozenset({'User'})
for c in registry._NODE_CLASS_REGISTRY:
    if c == base_user:
        registry._NODE_CLASS_REGISTRY.pop(base_user)
        break


# Extension of User model for accounting in API login/logout
class User(UserBase):

    belongs_to = RelationshipTo(
        'Group', 'BELONGS_TO', cardinality=ZeroOrMore, show=True)


class RelationTest(StructuredRel):
    pp = StringProperty(show=True)


class Group(IdentifiedNode):
    name = StringProperty(required=True, unique_index=True, show=True)
    extra = StringProperty(required=True, unique_index=True, show=False)
    members = RelationshipFrom(
        'User', 'BELONGS_TO', cardinality=ZeroOrMore, show=True)

    test1 = RelationshipTo(
        'JustATest', 'TEST', cardinality=OneOrMore,
        show=True, model=RelationTest)
    test2 = RelationshipTo(
        'JustATest', 'TEST2', cardinality=OneOrMore,
        show=False, model=RelationTest)


class JustATest(TimestampedNode):
    p_str = StringProperty(required=True, show=True)
    p_int = IntegerProperty()
    p_arr = ArrayProperty()
    p_json = JSONProperty()
    p_float = FloatProperty()
    p_date = DateProperty()
    p_dt = DateTimeProperty()
    p_bool = BooleanProperty()
    p_alias = AliasProperty()

    test1 = RelationshipFrom(
        'Group', 'TEST', cardinality=ZeroOrMore, model=RelationTest)

    test2 = RelationshipFrom(
        'Group', 'TEST2', cardinality=ZeroOrMore, model=RelationTest)

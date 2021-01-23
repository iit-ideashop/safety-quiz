import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker, relationship
_base_reservation = declarative_base()

from typing import Union, Callable, Tuple, Optional

# Just for type-hinting, if you know a better way please fix
class HasRemoveMethod:
    def remove(self):
        pass

def init_reservation_db(connection_string: str) -> Union[Callable[[], sa.orm.Session], HasRemoveMethod]:
    global engine
    engine = sa.create_engine(connection_string, pool_size=50, max_overflow=150, pool_recycle=3600, encoding='utf-8')
    db_session = scoped_session(sessionmaker(bind=engine))
    _base_reservation.metadata.create_all(engine)
    db = db_session()
    db.close()
    return db_session


class ReservationType(_base_reservation):
    __tablename__ = 'reservation_types'
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    name = sa.Column(sa.VARCHAR(100), nullable=False)
    quantity = sa.Column(sa.Integer, nullable=False, default=1)
    capacity = sa.Column(sa.Integer, nullable=False, default=1)

    reservations = relationship("Reservations", lazy='joined')

    def __repr__(self):
        return self.name

class ReservationWindow(_base_reservation):
    __tablename__ = 'reservation_windows'
    start = sa.Column(sa.DateTime, nullable=False, primary_key=True)
    end = sa.Column(sa.DateTime, nullable=False, primary_key=True)

    def __repr__(self):
        return ("Reservation window %s -> %s" % (self.start,self.end))

class Reservations(_base_reservation):
    __tablename__ = 'reservations'
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    start = sa.Column(sa.DateTime, nullable=False)
    end = sa.Column(sa.DateTime, nullable=False)
    sid = sa.Column(sa.Integer, nullable=False)
    type_id = sa.Column(sa.Integer, sa.ForeignKey('reservation_types.id'), nullable=False)
    parent_id = sa.Column(sa.Integer, sa.ForeignKey('reservations.id'), nullable=True)

    type = relationship('ReservationType')

    def __repr__(self):
        return "%s has a %s reservation from %s to %s" % (self.sid, self.type.name, self.start, self.end)
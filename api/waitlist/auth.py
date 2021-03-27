from functools import wraps
from typing import Callable, TypeVar, Any, Tuple, cast, Optional, Dict, Set
from flask import Blueprint, request, session, g
import requests
from .data import esi, database, config

bp = Blueprint("auth", __name__)
req_session = requests.Session()

REDIR_URI = config.CONFIG["esi"]["url"]
LOGIN_SCOPES = [
    "publicData",
    "esi-skills.read_skills.v1",
    "esi-clones.read_implants.v1",
]
FC_SCOPES = [
    "esi-fleets.read_fleet.v1",
    "esi-fleets.write_fleet.v1",
    "esi-ui.open_window.v1",
]

LOGIN_URL_FMT = (
    "https://login.eveonline.com/oauth/authorize?response_type=code"
    + "&redirect_uri={redir_uri}&client_id={client_id}&scope={scopes}&state={state}"
)

ACCESS_LEVELS: Dict[str, Set[str]] = {}
ACCESS_LEVELS["user"] = set()
ACCESS_LEVELS["trainee"] = ACCESS_LEVELS["user"] | set(
    [
        "fleet-configure",
        "fleet-invite",
        "fleet-view",
        "pilot-view",
        "waitlist-view",
    ]
)
ACCESS_LEVELS["fc"] = ACCESS_LEVELS["trainee"] | set(
    [
        "bans-view",
        "fit-history-view",
        "fit-view",
        "search",
        "skill-history-view",
        "skill-view",
        "waitlist-edit",
        "waitlist-manage",
    ]
)
ACCESS_LEVELS["council"] = ACCESS_LEVELS["fc"] | set(
    [
        "bans-manage",
        "access-manage",
    ]
)
ACCESS_LEVELS["admin"] = ACCESS_LEVELS["council"] | set([])

DecoratorType = TypeVar("DecoratorType", bound=Callable[..., Any])


def has_access(permission: str) -> bool:
    return permission in ACCESS_LEVELS[g.access_level]


def login_required(func: DecoratorType) -> DecoratorType:
    @wraps(func)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        # Never logged in
        if "account_id" not in session:
            return "Not logged in", 401

        g.account_id = session["account_id"]

        admin_record = (
            g.db.query(database.Administrator)
            .filter(database.Administrator.character_id == g.account_id)
            .one_or_none()
        )
        if admin_record:
            g.access_level = admin_record.level
        else:
            g.access_level = "user"

        return func(*args, **kwargs)

    return cast(DecoratorType, decorated)


def require_permission(permission: str) -> Callable[[DecoratorType], DecoratorType]:
    def decorator(func: DecoratorType) -> DecoratorType:
        @wraps(func)
        def decorated(*args: Any, **kwargs: Any) -> Any:
            if not has_access(permission):
                return "Unauthorized", 401
            return func(*args, **kwargs)

        return cast(DecoratorType, decorated)

    return decorator


def select_character(
    override_permission: Optional[str] = None,
) -> Callable[[DecoratorType], DecoratorType]:
    def decorator(func: DecoratorType) -> DecoratorType:
        @wraps(func)
        def decorated(*args: Any, **kwargs: Any) -> Any:
            if request.json:
                if not "character_id" in request.json:
                    return "Missing character_id in request", 400
                character_id = int(request.json["character_id"])
            else:
                if not "character_id" in request.args:
                    return "Missing character_id in request", 400
                character_id = int(request.args["character_id"])

            if character_id != g.account_id and not (
                override_permission and has_access(override_permission)
            ):
                if (
                    not g.db.query(database.AltCharacter)
                    .filter(
                        database.AltCharacter.account_id == g.account_id,
                        database.AltCharacter.alt_id == character_id,
                    )
                    .one_or_none()
                ):
                    return "Not allowed to query this character_id", 401

            g.character_id = character_id
            return func(*args, **kwargs)

        return cast(DecoratorType, decorated)

    return decorator


@bp.route("/api/auth/login_url")
def login_url() -> str:
    scopes = []
    scopes += LOGIN_SCOPES
    state = ""

    if "fc" in request.args:
        scopes += FC_SCOPES
    if "alt" in request.args:
        state = "alt"

    return LOGIN_URL_FMT.format(
        redir_uri=REDIR_URI, client_id=esi.AUTH_ID, scopes=" ".join(scopes), state=state
    )


@bp.route("/api/auth/cb", methods=["POST"])
def callback() -> Tuple[str, int]:
    _access_token, _refresh_token, character_id = esi.process_auth(
        "authorization_code", request.json["code"]
    )

    if "state" in request.json and request.json["state"] == "alt":
        if "account_id" not in session:
            session["account_id"] = character_id

        if session["account_id"] != character_id:
            alt = database.AltCharacter(
                account_id=session["account_id"], alt_id=character_id
            )
            g.db.merge(alt)
            g.db.commit()

    else:
        session["account_id"] = character_id
        session.permanent = True

    return "OK", 200


@bp.route("/api/auth/whoami")
@login_required
def whoami() -> Tuple[Any, int]:
    char = (
        g.db.query(database.Character)
        .filter(database.Character.id == session["account_id"])
        .one_or_none()
    )
    if not char:
        return "Character data missing from db", 401

    characters = [
        {
            "id": char.id,
            "name": char.name,
        }
    ]
    for _alt_record, alt_character in (
        g.db.query(database.AltCharacter, database.Character)
        .join(database.AltCharacter.alt)
        .filter(database.AltCharacter.account_id == char.id)
    ):
        characters.append({"id": alt_character.id, "name": alt_character.name})

    return {
        "account_id": g.account_id,
        "access": sorted(ACCESS_LEVELS[g.access_level]),
        "characters": characters,
    }, 200


@bp.route("/api/auth/logout")
def logout() -> str:
    if "account_id" in session:
        account_id = session["account_id"]
        g.db.query(database.AltCharacter).filter(
            database.AltCharacter.account_id == account_id
        ).delete()
        g.db.query(database.AltCharacter).filter(
            database.AltCharacter.alt_id == account_id
        ).delete()
        g.db.commit()
    session.clear()
    return "OK"

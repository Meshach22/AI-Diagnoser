"""backend/auth_cli.py

Command-line administrative utility for AI-Diagnoser user management.
Usage:
    python -m backend.auth_cli create-user --email user@example.com --name "Jane Doe" --password "SecurePass1234!"
    python -m backend.auth_cli list-users
    python -m backend.auth_cli set-password --email user@example.com --password "NewSecurePass1234!"
    python -m backend.auth_cli delete-user --email user@example.com
"""

import argparse
import sys
from backend.services.auth_service import AuthError, get_auth_service


def main():
    parser = argparse.ArgumentParser(description="AI-Diagnoser User Management CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create-user
    create_p = subparsers.add_parser("create-user", help="Create a new user")
    create_p.add_argument("--email", required=True, help="User email address")
    create_p.add_argument("--name", required=True, help="User display name")
    create_p.add_argument("--password", required=True, help="Password (min 12 chars)")
    create_p.add_argument("--admin", action="store_true", help="Grant administrative privileges")

    # list-users
    subparsers.add_parser("list-users", help="List all registered users")

    # set-role
    role_p = subparsers.add_parser("set-role", help="Set role for an existing user")
    role_p.add_argument("--email", required=True, help="User email address")
    role_p.add_argument("--role", choices=["user", "admin"], required=True, help="User role (user or admin)")

    # set-password
    set_p = subparsers.add_parser("set-password", help="Reset password for an existing user")
    set_p.add_argument("--email", required=True, help="User email address")
    set_p.add_argument("--password", required=True, help="New password (min 12 chars)")

    # delete-user
    del_p = subparsers.add_parser("delete-user", help="Delete a user")
    del_p.add_argument("--email", required=True, help="User email address")

    args = parser.parse_args()
    service = get_auth_service()

    try:
        if args.command == "create-user":
            u = service.create_user(args.email, args.name, args.password, role="admin" if args.admin else "user", is_admin=args.admin)
            print(f"[SUCCESS] User created: id={u['id']} email={u['email']} name={u['name']} role={u['role']} admin={u['is_admin']}")
        elif args.command == "list-users":
            users = service.list_users()
            print(f"Total registered users: {len(users)}")
            for u in users:
                print(f"  - [{u['id']}] {u['name']} <{u['email']}> (role: {u.get('role', 'user')}, admin: {u.get('is_admin', False)}, active: {bool(u['is_active'])})")
        elif args.command == "set-role":
            ok = service.set_role(args.email, args.role, is_admin=(args.role == "admin"))
            if ok:
                print(f"[SUCCESS] User {args.email} role updated to {args.role}.")
            else:
                print(f"[ERROR] User not found: {args.email}", file=sys.stderr)
                sys.exit(1)
        elif args.command == "set-password":
            ok = service.set_password(args.email, args.password)
            if ok:
                print(f"[SUCCESS] Password updated for {args.email} (all existing sessions revoked).")
            else:
                print(f"[ERROR] User not found: {args.email}", file=sys.stderr)
                sys.exit(1)
        elif args.command == "delete-user":
            ok = service.delete_user(args.email)
            if ok:
                print(f"[SUCCESS] User {args.email} deleted.")
            else:
                print(f"[ERROR] User not found: {args.email}", file=sys.stderr)
                sys.exit(1)
    except AuthError as e:
        print(f"[AUTH ERROR] {e.message}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

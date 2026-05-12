import os


ENV_PATH = '.env'


def main():
    if os.path.exists(ENV_PATH):
        answer = input(f'{ENV_PATH} already exists. Overwrite? [y/N]: ').strip().lower()
        if answer != 'y':
            print('Cancelled.')
            return

    print('Enter a SECRET_KEY for Flask sessions and CSRF.')
    print('Pick a long random string (32+ chars). Example:')
    print('  3f8a9c2e1b4d6f7a8c9e0b1d2f3a4c5e6b7d8f9a0c1e2b3d4f5a6c7e8b9d0f1a')
    key = input('SECRET_KEY: ').strip()

    if not key:
        print('No key entered. Cancelled.')
        return

    with open(ENV_PATH, 'w') as f:
        f.write(f'SECRET_KEY={key}\n')

    print(f'Wrote {ENV_PATH}.')


if __name__ == '__main__':
    main()

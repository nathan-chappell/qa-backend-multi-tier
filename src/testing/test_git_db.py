# testing/test_git_db.py

from qa_server.services import

async def test():
    import json
    import subprocess
    git_dir = str(uuid4())
    git_client = GitClient(git_dir)
    if Path(git_dir).exists():
        raise RuntimeError(f'about to step on {git_dir}')
    try:
        response = await git_client.create("this is a test",'test.txt')
        print(f"{response}")

        response = await git_client.update('test.txt',['this aint no test!', 'yo momma so fat'])
        try:
            body = json.loads(response.body)
        except:
            print('[JSON]: ' + response.body)
        print(f"{response}, {body}")
        docIds = body['docIds']

        response = await git_client.read('*')
        body = json.loads(response.body)
        print(f"{response}, {body}")

        for docId in docIds:
            response = await git_client.read(docId)
            body = json.loads(response.body)
            print(f"{response}, {body}")

            response = await git_client.delete(docId)
            print(f"{response}")
    finally:
        subprocess.run(['rm','-rf',git_dir],check=True)



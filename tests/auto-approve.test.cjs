const assert = require('node:assert/strict')
const { readFileSync } = require('node:fs')
const { join } = require('node:path')
const { test } = require('node:test')

const workflow = readFileSync(
  join(__dirname, '../.github/workflows/Auto-Approve-and-merge-jzdxjk.yml'),
  'utf8',
)
const scriptBlock = workflow.match(/          script: \|\r?\n((?: {12}[^\r\n]*\r?\n|\r?\n)+)/)
assert.ok(scriptBlock, 'The approval script must be present in the workflow')
const script = scriptBlock[1].replace(/^ {12}/gm, '')
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const runScript = new AsyncFunction('context', 'github', 'core', script)

async function lookup(pullRequests, eventName = 'workflow_run') {
  const calls = []
  const closedPr = { number: 61, state: 'closed' }
  await runScript({
    eventName,
    repo: { owner: 'jzdxjk', repo: 'Jav-Actors-Mapping' },
    payload: {
      repository: { id: 100 },
      pull_request: closedPr,
      workflow_run: {
        pull_requests: pullRequests,
        head_repository: { owner: { login: 'jzdxjk' } },
        head_branch: 'pr-xml-only',
      },
    },
  }, {
    rest: {
      pulls: {
        async get(args) {
          calls.push(['get', args])
          assert.equal(args.pull_number, 61, 'Foreign PR numbers must never be queried in the local repository')
          return { data: closedPr }
        },
        async list(args) {
          calls.push(['list', args])
          return { data: [] }
        },
      },
    },
  }, { info() {} })
  return calls
}

const foreignPr = { number: 60, base: { repo: { id: 200 } } }
const localPr = { number: 61, base: { repo: { id: 100 } } }

test('foreign PR references fall back to a local repository search', async () => {
  const calls = await lookup([foreignPr])
  assert.deepEqual(calls, [['list', {
    owner: 'jzdxjk',
    repo: 'Jav-Actors-Mapping',
    state: 'open',
    head: 'jzdxjk:pr-xml-only',
    per_page: 1,
  }]])
})

test('a local PR is selected even when a foreign PR is listed first', async () => {
  const calls = await lookup([foreignPr, localPr])
  assert.equal(calls[0][0], 'get')
  assert.equal(calls[0][1].pull_number, 61)
})

test('runs without PR references still search the current repository', async () => {
  assert.equal((await lookup([]))[0][0], 'list')
})

test('pull_request_target uses the PR supplied by its own repository', async () => {
  assert.deepEqual(await lookup([foreignPr], 'pull_request_target'), [])
})

async function mergeWithWorkflowSha(workflowSha) {
  const calls = []
  const pullRequest = {
    number: 61, state: 'open', draft: false, user: { login: 'jzdxjk' },
    head: { sha: 'latest-head' }, base: { ref: 'main' },
  }
  await runScript({
    eventName: 'workflow_run',
    repo: { owner: 'jzdxjk', repo: 'Jav-Actors-Mapping' },
    payload: {
      repository: { id: 100 },
      workflow_run: { pull_requests: [localPr], head_sha: workflowSha },
    },
  }, {
    async paginate() {
      calls.push('files')
      return [{ filename: 'actor-mapping.xml' }]
    },
    rest: {
      pulls: {
        async get() { return { data: pullRequest } },
        async createReview() { calls.push('approve') },
        async merge(args) {
          calls.push(['merge', args.sha])
          return { data: { merged: true } }
        },
      },
    },
  }, { info() {}, setOutput() {} })
  return calls
}

test('an older successful workflow cannot approve or merge a newer PR head', async () => {
  assert.deepEqual(await mergeWithWorkflowSha('older-head'), [])
})

test('a successful workflow for the current PR head merges the checked commit', async () => {
  assert.deepEqual(await mergeWithWorkflowSha('latest-head'), [
    'files', 'approve', ['merge', 'latest-head'],
  ])
})

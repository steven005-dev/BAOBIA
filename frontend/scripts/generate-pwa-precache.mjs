import { readdir, writeFile } from 'node:fs/promises'
import { join, relative, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const rootPath = fileURLToPath(new URL('../dist/', import.meta.url))

async function listFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true })
  const nested = await Promise.all(
    entries.map((entry) => {
      const path = join(directory, entry.name)
      return entry.isDirectory() ? listFiles(path) : [path]
    }),
  )
  return nested.flat()
}

const files = await listFiles(rootPath)
const assets = files
  .map((path) => `/${relative(rootPath, path).split(sep).join('/')}`)
  .filter((path) => path !== '/precache-manifest.json')

await writeFile(
  join(rootPath, 'precache-manifest.json'),
  `${JSON.stringify({ assets }, null, 2)}\n`,
)

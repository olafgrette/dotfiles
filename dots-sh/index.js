// dots.oag.sh — serves this repository's init.sh, so that
//
//   curl -fsSL dots.oag.sh | sh
//
// bootstraps a machine. The script itself stays in GitHub and is fetched per
// request, so pushing to main updates what this serves with no deploy step.
//
// Serving from GitHub rather than from a machine at home is deliberate:
// init.sh already clones over HTTPS from github.com, so GitHub is a hard
// dependency of the flow either way. A self-hosted origin would add a second
// one that is offline exactly when a machine is being rebuilt.

const SOURCE = "https://raw.githubusercontent.com/olafgrette/dotfiles/main/init.sh";

// curl -f suppresses the body on a 4xx/5xx, so an error is a no-op at the far
// end of the pipe rather than a fragment of shell. The text is a valid script
// regardless, for anyone who fetches without -f.
const UNAVAILABLE = "# dots.oag.sh could not fetch init.sh\nexit 1\n";

function plain(body, status) {
  return new Response(body, {
    status,
    headers: { "content-type": "text/plain; charset=utf-8" },
  });
}

export default {
  async fetch() {
    let upstream;

    try {
      upstream = await fetch(SOURCE, {
        cf: { cacheTtl: 300, cacheEverything: true },
      });
    } catch (error) {
      console.error({ event: "upstream_threw", error: String(error) });
      return plain(UNAVAILABLE, 502);
    }

    if (!upstream.ok) {
      console.error({ event: "upstream_status", status: upstream.status });
      return plain(UNAVAILABLE, 502);
    }

    // Stream the body through rather than buffering it. init.sh is small, but
    // reading a response into memory is the habit that breaks on the file that
    // is not.
    return new Response(upstream.body, {
      headers: {
        "content-type": "text/plain; charset=utf-8",
        "cache-control": "public, max-age=300",
      },
    });
  },
};

"""Bound an acquisition source without leaving child download processes behind."""
import argparse, os, signal, subprocess, sys


def run(command, timeout):
    child=subprocess.Popen(command,start_new_session=True)
    def stop():
        try:os.killpg(child.pid,signal.SIGTERM)
        except ProcessLookupError:return
        try:child.wait(timeout=3)
        except subprocess.TimeoutExpired:pass
        try:os.killpg(child.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        child.wait()
    def interrupted(signum,frame):
        stop();raise SystemExit(128+signum)
    previous={s:signal.signal(s,interrupted) for s in (signal.SIGTERM,signal.SIGINT)}
    try:
        try:return child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            stop();print(f'Source time budget reached ({timeout}s); continuing with other sources.',flush=True);return 124
    finally:
        for s,handler in previous.items():signal.signal(s,handler)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeout',type=float,default=90)
    parser.add_argument('command',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    command=args.command[1:] if args.command[:1]==['--'] else args.command
    if not command or args.timeout<=0:parser.error('Provide a command and positive timeout')
    raise SystemExit(run(command,args.timeout))

# Torrentula: A BitTorrent Client

## Getting started

The **BitTorrent client** can be used in two ways: as a command-line script or imported as a package into other Python code.

#### Quick Start
```python
python -m torrentula --torr tests/fixtures/debian-mac.torrent
```

#### Running as a Script
When run as a script, you can pass command-line arguments. The entry point is `__main__.py`. The `destination` argument is optional and defaults to the current directory from which the client is executed.

```python
python -m torrentula --torr <your-torrent.torrent> --dest <download-directory>
```

- --torr <your-torrent.torrent>: The path to the torrent file.
- --dest <download-directory>: The directory where the files will be downloaded. If not specified, it defaults to the current directory.

#### Importing as a Package

You can also import the package programmatically into other Python code. In this case, __main__.py is ignored, and __init__.py is invoked, exposing the functions imported inside __init__.py to the scope of your code.

```python
import torrentula
torrentula.download_torrent(<your-torrent.torrent>, <download-directory>)
```
This method allows for integration of the torrent client directly within Python applications.

### Development

#### Running Tests
The library tests can be automatically discovered and ran by the unittests library. Example torrents for testing are in the fixtures folder.
```python
python -m unittest discover -s tests
```


# Work in Progress:


## Name

## Description

## Badges

## Visuals

## Installation

## Usage

## Support

## Roadmap

## Contributing

## Authors and acknowledgment

## License

## Project status

import os
import sys
import struct
import bluetooth._bluetooth as _bt

def write_scan_enable(hci_sock, mode):
    #mode: 0 - piscan disabled; 1 - iscan enabled; 2 - pscan enabled; 3 - piscan enabled
    old_filter = hci_sock.getsockopt( _bt.SOL_HCI, _bt.HCI_FILTER, 14)
    flt = _bt.hci_filter_new()
    opcode = _bt.cmd_opcode_pack(_bt.OGF_HOST_CTL, 
            _bt.OCF_WRITE_SCAN_ENABLE)
    _bt.hci_filter_set_ptype(flt, _bt.HCI_EVENT_PKT)
    _bt.hci_filter_set_event(flt, _bt.EVT_CMD_COMPLETE);
    _bt.hci_filter_set_opcode(flt, opcode)
    hci_sock.setsockopt( _bt.SOL_HCI, _bt.HCI_FILTER, flt )

    _bt.hci_send_cmd(hci_sock, _bt.OGF_HOST_CTL, _bt.OCF_WRITE_SCAN_ENABLE, struct.pack("B", mode) )

    pkt = hci_sock.recv(255)

    status = struct.unpack("xxxxxxB", pkt)[0]

    # restore old filter
    hci_sock.setsockopt( _bt.SOL_HCI, _bt.HCI_FILTER, old_filter )
    if status != 0: return -1
    return 0

def set_visible():
    #mode = 3 when piscan enabled
    dev_id = 0
    hci_sock = _bt.hci_open_dev(dev_id)
    write_scan_enable(hci_sock, 3)

def unset_visible():
    #mode = 2 when only iscan disabled
    dev_id = 0
    hci_sock = _bt.hci_open_dev(dev_id)
    write_scan_enable(hci_sock, 2)

if __name__ == "__main__":
    set_visible()

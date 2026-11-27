; benchmark generated from python API
(set-info :status unknown)
(declare-fun x () Int)
(declare-fun q () Int)
(declare-fun y () Int)
(declare-fun r () Int)
(assert
 (>= x 0))
(assert
 (>= q 0))
(assert
 (>= y 0))
(assert
 (>= r 0))
(assert
 (<= x 255))
(assert
 (<= q 255))
(assert
 (<= y 255))
(assert
 (<= r 255))
(assert
 (or (< (* (- x q) (- x q)) 0) (> (* (- x q) (- x q)) 65025)))
(check-sat)
